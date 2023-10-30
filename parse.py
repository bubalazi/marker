import argparse

import fitz as pymupdf
from marker.extract_text import get_text_blocks
from marker.headers import categorize_blocks, filter_header_footer
from marker.equations import replace_equations, load_nougat_model
from marker.segmentation import detect_all_block_types, load_layout_model
from marker.code import identify_code_blocks, indent_blocks
from marker.markdown import merge_spans, merge_lines, get_full_text
from marker.schema import Page, BlockType
from typing import List
from copy import deepcopy


def annotate_spans(blocks: List[Page], block_types: List[BlockType]):
    for i, page in enumerate(blocks):
        page_block_types = block_types[i]
        page.add_block_types(page_block_types)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="PDF file to parse")
    parser.add_argument("output", help="Output file name")
    args = parser.parse_args()

    fname = args.filename
    doc = pymupdf.open(fname)
    blocks, toc = get_text_blocks(doc)

    layoutlm_model = load_layout_model()
    block_types = detect_all_block_types(doc, blocks, layoutlm_model)

    filtered = deepcopy(blocks)
    annotate_spans(filtered, block_types)
    identify_code_blocks(filtered)
    indent_blocks(filtered)

    bad_span_ids = categorize_blocks(blocks)
    bad_span_ids += filter_header_footer(blocks)

    # Copy to avoid changing original data

    for page in filtered:
        for block in page.blocks:
            block.filter_spans(bad_span_ids)
            block.filter_bad_span_types(block_types[page.pnum])

    nougat_model = load_nougat_model()
    filtered = replace_equations(doc, filtered, block_types, nougat_model)

    # Copy to avoid changing original data
    merged_lines = merge_spans(filtered)
    text_blocks = merge_lines(merged_lines, filtered)
    full_text = get_full_text(text_blocks)

    with open(args.output, "w+") as f:
        f.write(full_text)