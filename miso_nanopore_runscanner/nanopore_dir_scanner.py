import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import pendulum
import pod5
import polars as pl

from miso_nanopore_runscanner.config import PARSE_SEQSUMMARY
from miso_nanopore_runscanner.models import RunResponse, RunStatus


def get_nanopore_runs(basedir: Path) -> Iterator[Path]:
    """Get Nanopore run directories that are 3 levels deep and have a pod5_pass directory."""
    for sdir in basedir.iterdir():
        if not sdir.is_dir():
            continue
        for ssdir in sdir.iterdir():
            if not ssdir.is_dir():
                continue
            for sssdir in ssdir.iterdir():
                if sssdir.is_dir() and (sssdir / "pod5_pass").exists():
                    yield sssdir


def find_final_summary_path(rundir: Path) -> Path | None:
    """Find the final_summary file in the run directory to read for its run info."""
    try:
        return next(rundir.glob("final_summary*.txt"))
    except StopIteration:
        return None


def find_pod5(rundir: Path) -> Path | None:
    """Find any pod5 file in the run directory to read for its run info."""
    try:
        return next(rundir.rglob("*.pod5"))
    except StopIteration:
        return None


def parse_run_summary(rundir: Path) -> dict | None:
    final_summary_path = find_final_summary_path(rundir)
    if final_summary_path:
        return {kv[0]: kv[1] for line in final_summary_path.read_text().splitlines() if
                (kv := line.strip().split('=')) and len(kv) == 2}
    return None


def parse_seqsummary(seqsummary_path: Path) -> list[dict]:
    with open(seqsummary_path) as f:
        headers: list[str]
        for header_line in f:
            headers = header_line.split('\t')
            break
        header_index = {header: i for i, header in enumerate(headers)}
        barcode_index = header_index['alias']
        read_length_index = header_index['sequence_length_template']
        barcode_stats = defaultdict(lambda: defaultdict(int))
        for line in f:
            sp = line.strip().split('\t')
            if len(sp) != len(headers):
                continue
            barcode = sp[barcode_index]
            read_length = int(sp[read_length_index])
            barcode_stats[barcode]['sum_read_length'] += read_length
            barcode_stats[barcode]['count'] += 1
    out = []
    ordered_barcodes = list(barcode_stats.keys())
    ordered_barcodes.sort()
    for barcode in ordered_barcodes:
        stats = barcode_stats[barcode]
        sum_len = stats['sum_read_length']
        n = stats['count']
        out.append({
            'barcode': barcode,
            'mean_length': sum_len / n,
            'number_of_reads': n
        })
    return out


def parse_pod5_metadata(pod5_path: Path) -> dict | None:
    try:
        with pod5.Reader(pod5_path) as reader:
            return reader.run_info_table.read_all().to_pydict()
    except Exception:
        return None


def get_software(p5_md: dict) -> str:
    try:
        return p5_md['software'][0]
    except KeyError or IndexError:
        return ""


def get_container_model(p5_md: dict) -> str:
    try:
        return p5_md['flow_cell_product_code'][0]
    except KeyError or IndexError:
        return ""


def get_container_serial(p5_md: dict) -> str:
    try:
        return p5_md['flow_cell_id'][0]
    except KeyError or IndexError:
        return ""


def get_run_alias(rundir: Path) -> str:
    return f"{rundir.parent.parent.name}_{rundir.parent.name}_{rundir.name}"


def get_start_date(p5_md: dict) -> str:
    from datetime import datetime
    try:
        dt: datetime = p5_md['protocol_start_time'][0]
        return datetime.strftime(dt, "%Y-%m-%dT%H:%M:%S.%fZ")
    except KeyError or IndexError:
        return ""


def get_protocol_version(p5_md: dict) -> str:
    try:
        return p5_md['protocol_name'][0]
    except KeyError or IndexError:
        return ""


def get_sequencer_name(p5_md: dict) -> str:
    try:
        return p5_md['sequencer_position'][0]
    except KeyError or IndexError:
        return ""


def get_sequencing_kit(p5_md: dict) -> str:
    try:
        return p5_md['sequencing_kit'][0]
    except KeyError or IndexError:
        return ""


def create_metrics_table_dict(entries: list[dict]) -> dict:
    """Create a dict that MISO can turn in a DataTables HTML table on the Run page under Metrics.

    The dict has the following structure:

    {
        "type": "table",
        "columns": [{"name": "COLUMN_NAME", "property": "COLUMN_NAME"}, ...],
        "rows": [{"COLUMN_NAME": "VALUE", ...}]
    }

    Args:
        entries: A list of dicts with the same keys

    Returns:
        A dict that MISO can turn in a DataTables HTML table on the Run page
    """
    if not entries:
        return {}
    columns = list(entries[0].keys())
    return dict(
        columns=[dict(name=x, property=x) for x in columns],
        type='table',
        rows=entries,
    )


def create_run_response(rundir: Path) -> RunResponse:
    is_completed = False
    completion_date = None
    run_alias = get_run_alias(rundir)
    run_summary = parse_run_summary(rundir)
    metrics = []
    if run_summary:
        is_completed = True
        dt = pendulum.parse(run_summary['processing_stopped'] if 'processing_stopped' in run_summary else run_summary[
            'acquisition_stopped']).astimezone(pendulum.UTC)
        completion_date = pendulum.timezone('UTC').convert(dt).to_iso8601_string()
    if PARSE_SEQSUMMARY:
        seqsummary_path = next(rundir.glob("sequencing_summary*.txt"))
        if seqsummary_path.exists():
            barcode_stats = parse_seqsummary(seqsummary_path)
            metrics.append(create_metrics_table_dict(barcode_stats))

    pod5_path = find_pod5(rundir)
    p5_md = parse_pod5_metadata(pod5_path)
    start_date = get_start_date(p5_md)
    sequencing_kit = get_sequencing_kit(p5_md)
    software = get_software(p5_md)
    container_model = get_container_model(p5_md)
    container_serial = get_container_serial(p5_md)
    protocol_version = get_protocol_version(p5_md)
    sequencer_name = get_sequencer_name(p5_md)

    start_dt = pendulum.parse(start_date).astimezone(pendulum.UTC)
    today = pendulum.now()
    run_status = RunStatus.COMPLETED if is_completed else RunStatus.RUNNING
    if completion_date is None and today - start_dt >= pendulum.duration(days=7):
        run_status = RunStatus.STOPPED
    return RunResponse(
        runAlias=run_alias,
        sequencerFolderPath=str(rundir.resolve().absolute()),
        startDate=start_date,
        completionDate=completion_date,
        sequencingKit=sequencing_kit,
        software=software,
        containerModel=container_model,
        containerSerialNumber=container_serial,
        healthType=run_status,
        protocolVersion=protocol_version,
        sequencerName=sequencer_name,
        metrics=json.dumps(metrics) if metrics else None,
    )
