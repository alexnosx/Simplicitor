# templates_engine/breakdown.py
# Phase D-F: PPTX structural inspector, content stripping, draft manifest generation.


def inspect_pptx(path):
    raise NotImplementedError


def format_inspection(report):
    raise NotImplementedError


def strip_to_template(path, out_path):
    raise NotImplementedError


def score_layouts(inspection):
    raise NotImplementedError


def generate_draft_manifest(inspection, scoring, template_file):
    raise NotImplementedError


def detection_report(inspection, scoring):
    raise NotImplementedError


def hard_stop_result():
    raise NotImplementedError
