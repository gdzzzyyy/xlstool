# -*- coding: utf-8 -*-
#!/usr/bin/env python
# File Name: xlstool.py
# Author: Stan.Lch
# Mail: fn.stanc@gmail.com
# Created Time: 2018/7/12 0:03:45

import sys
import os
import getopt
import logging
import shutil
import subprocess
import xlrd

reload(sys)
sys.setdefaultencoding("utf-8")

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger()
LOG_DEBUG = logger.debug
LOG_INFO = logger.info
LOG_WARN = logger.warning
LOG_ERR = logger.error

PROTO_OUTPUT_PATH = "./output/proto/"
BYTES_OUTPUT_PATH = "./output/bytes/"
PYTHON_OUTPUT_PATH = "./output/py/"
CS_OUTPUT_PATH = "./output/cs/"

FIELD_COMMENT_ROW = 0
FIELD_NAME_ROW = 1
FIELD_TYPE_ROW = 2
TAG_FILTER_ROW = 3
DATA_BEGIN_ROW = 4
DATA_BEGIN_COL = 1
ID_COL = 0

PROTOC_BIN = "protoc"
ID_FIELD_NAME = "id"
DATA_BLOCKS_STRUCT_NAME = "DataBlocks"
LOADER_CLASS_NAME = "DataCenter"
PACKAGE_NAME = "AppConfig"

INTEGER_TYPES = ["int32", "int64", "uint32", "uint64"]
FRACTION_TYPES = ["float", "double"]
SUPPORTED_TYPES = ["string"] + INTEGER_TYPES + FRACTION_TYPES


class FieldInfo:
    def __init__(self, fname, ftype, desc, cols):
        self.field_name = fname
        self.field_type = ftype
        self.desc = desc
        self.cols = cols


class SheetMeta:
    def __init__(self, sheet_name):
        self.sheet_name = sheet_name
        self.field_names = []
        self.field_types = {}
        self.field_cols = {}
        self.field_descs = {}

    def has_field(self, field_name):
        return field_name in self.field_names

    def add_field(self, field_name, field_type, desc):
        self.field_names.append(field_name)
        self.field_types[field_name] = field_type
        self.field_descs[field_name] = desc
        self.field_cols[field_name] = []

    def add_col_to_field(self, field_name, col):
        self.field_cols[field_name].append(col)

    def field_type(self, field_name):
        return self.field_types[field_name]

    def field_info(self, field_name):
        fi = FieldInfo(field_name, self.field_types[field_name],
                       self.field_descs[field_name], self.field_cols[field_name])
        return fi


def get_proto_path(sheet_name):
    file_name = sheet_name + ".proto"
    proto_file = os.path.join(PROTO_OUTPUT_PATH, file_name)
    return file_name, proto_file


def get_bytes_path(sheet_name):
    return os.path.join(BYTES_OUTPUT_PATH, sheet_name + ".bytes")


def parse_fields(sheet_name, sheet, tag):
    """
    Parse sheet headers and return field definitions.
    """
    LOG_DEBUG("Parsing fields...")
    sheet_meta = SheetMeta(sheet_name)

    ncols = sheet.ncols
    for i in range(DATA_BEGIN_COL, ncols):
        field_name = sheet.cell_value(
            FIELD_NAME_ROW, i).encode("utf-8").strip()

        if len(field_name) == 0:
            LOG_DEBUG("Skip col %s cause of empty field name" % i)
            continue

        field_name = field_name.replace(' ', '')

        if field_name == ID_FIELD_NAME:
            raise Exception("Reserved name: " + field_name)

        need_export_filed = True
        if field_name.startswith("#") or field_name.startswith("_"):
            need_export_filed = False
        elif tag is not None:
            curr_filed_tags = sheet.cell_value(
                TAG_FILTER_ROW, i).encode("utf-8").strip()
            need_export_filed = tag in curr_filed_tags

        if not need_export_filed:
            LOG_DEBUG("Skip col: %s,%s" % (field_name, i))
            continue

        field_type = sheet.cell_value(
            FIELD_TYPE_ROW, i).encode("utf-8").strip()

        if field_type not in SUPPORTED_TYPES:
            if field_type == "int":
                field_type = "int32"
            else:
                raise Exception("Unsupported type: field: %s, type: %s" % (
                    field_name, field_type))

        # merge fields if names and types are match
        if not sheet_meta.has_field(field_name):
            desc = unicode(sheet.cell_value(FIELD_COMMENT_ROW, i))
            sheet_meta.add_field(field_name, field_type, desc)
            sheet_meta.add_col_to_field(field_name, i)
        else:
            if field_type != sheet_meta.field_type(field_name):
                raise Exception(
                    "Field type is different from the same field before: field %s , type %s" % (field_name, field_type))
            sheet_meta.add_col_to_field(field_name, i)

    if len(sheet_meta.field_names) == 0:
        return None
    else:
        return sheet_meta


def output_proto_header(content, file_name):
    proto_header = (
        '''/*
* @file: %s
* @brief: This file is generated by xlstool, please don't edit it.
*/

syntax = "proto2";

package %s;

''')
    content.append(proto_header % (file_name, PACKAGE_NAME))


def output_struct_head(struct_name, content):
    content.append("message %s {\n" % struct_name)


def output_struct_tail(struct_name, content):
    content.append("}\n")


def output_field(field_info, field_index, content):
    field_rule = "optional"
    if len(field_info.cols) > 1:
        field_rule = "repeated"
    content.append("    %s %s %s = %s;\n" %
                   (field_rule, field_info.field_type, field_info.field_name, field_index))


def output_id_filed(content):
    fi = FieldInfo(ID_FIELD_NAME, "int32", "instance id", [1])
    output_field(fi, 1, content)


def gen_python_source(proto_file):
    cmd = "%s -I %s --python_out=%s %s"\
        % (PROTOC_BIN, PROTO_OUTPUT_PATH, PYTHON_OUTPUT_PATH, proto_file)
    subprocess.check_call(cmd, shell=False)


def gen_proto_for_sheet(sheet_meta):
    sheet_name = sheet_meta.sheet_name

    file_name, proto_file = get_proto_path(sheet_name)

    LOG_INFO("==> Generating proto: " + proto_file)
    content = []

    output_proto_header(content, file_name)

    output_struct_head(sheet_name, content)
    output_id_filed(content)

    field_index = 2
    for field_name in sheet_meta.field_names:
        fi = sheet_meta.field_info(field_name)
        output_field(fi, field_index, content)
        field_index += 1

    output_struct_tail(sheet_name, content)

    with open(proto_file, "w+") as f:
        f.writelines(content)

    gen_python_source(file_name)


def gen_proto(all_sheet_metas):
    imports = []
    message_body = []

    block_index = 1
    for f, sheet_metas in all_sheet_metas.items():
        for sheet_meta in sheet_metas:
            gen_proto_for_sheet(sheet_meta)
            sheet_name = sheet_meta.sheet_name
            imports.append("import \"%s.proto\";\n" % sheet_meta.sheet_name)
            message_body.append(
                "    repeated %s %s_items = %s;\n" % (sheet_name, sheet_name, block_index))
            block_index = block_index + 1

    fname, fpath = get_proto_path(DATA_BLOCKS_STRUCT_NAME)
    with open(fpath, "w+") as f:
        content = []
        output_proto_header(content, fname)
        content.extend(imports)
        content.append("\n")
        output_struct_head(DATA_BLOCKS_STRUCT_NAME, content)
        content.extend(message_body)
        output_struct_tail(DATA_BLOCKS_STRUCT_NAME, content)
        f.writelines(content)
    gen_python_source(fname)


def get_field_value(cell, field_type):
    if field_type == "string":
        return unicode(cell.value)

    if cell.ctype == 0:
        return 0
    elif cell.ctype == 1 or cell.ctype == 2:
        try:
            if field_type in INTEGER_TYPES:
                return int(cell.value)
            elif field_type in FRACTION_TYPES:
                return float(cell.value)
        finally:
            return 0

    print cell.value
    print cell.ctype
    raise Exception("type error")
    return None


def parse_row(sheet, row, item_id, sheet_meta, item):
    # LOG_DEBUG("parsing row %s, id %s" % (row, item_id))
    item.__setattr__(ID_FIELD_NAME, item_id)
    for field_name in sheet_meta.field_names:
        fi = sheet_meta.field_info(field_name)
        cols = fi.cols
        field_type = fi.field_type
        # LOG_DEBUG("parsing row: field_name = " + field_name)
        if len(cols) == 1:
            cell = sheet.cell(row, cols[0])
            item.__setattr__(field_name, get_field_value(cell, field_type))
        else:
            for col in cols:
                cell = sheet.cell(row, col)
                item.__getattribute__(field_name).append(
                    get_field_value(cell, field_type))


def load_pymodule(struct_name):
    module_name = struct_name + "_pb2"
    exec("from %s import *" % module_name)
    module = sys.modules[module_name]
    return module


def gen_binary(all_sheet_metas):
    data_blocks_module = load_pymodule(DATA_BLOCKS_STRUCT_NAME)
    data_blocks = getattr(data_blocks_module, DATA_BLOCKS_STRUCT_NAME)()
    for f, sheet_metas in all_sheet_metas.items():
        workbook = xlrd.open_workbook(f)
        for sheet_meta in sheet_metas:
            sheet_name = sheet_meta.sheet_name
            sheet = workbook.sheet_by_name(sheet_name)
            items = data_blocks.__getattribute__(sheet_name + "_items")
            LOG_INFO("==> Export data from: %s - %s" % (sheet_name, f))
            index = 0
            for row in range(DATA_BEGIN_ROW, sheet.nrows):
                id_cell = sheet.cell(row, ID_COL)
                if id_cell.ctype != 2:
                    LOG_DEBUG("Skip row with non-number id, row: %s" % row)
                    continue
                item_id = int(id_cell.value)
                item = items.add()
                parse_row(sheet, row, item_id, sheet_meta, item)
                index += 1

    data = data_blocks.SerializeToString()
    bytes_path = get_bytes_path(LOADER_CLASS_NAME)

    LOG_INFO("==> Generating bytes: " + bytes_path)
    with open(bytes_path, "wb+") as f:
        f.write(data)


def files_within(file_path, pattern="*"):
    import os
    import fnmatch

    if os.path.isfile(file_path):
        yield file_path
    else:
        for dirpath, dirnames, filenames in os.walk(file_path):
            for file_name in fnmatch.filter(filenames, pattern):
                yield os.path.join(dirpath, file_name)


def parse_xls_sheet_meta(file_path, tag):
    all_sheet_names = {}
    all_sheet_metas = {}
    for xls_file_path in files_within(file_path, pattern="*.xls"):
        LOG_INFO("==> Parsing sheet meta for file: " + xls_file_path)
        workbook = xlrd.open_workbook(xls_file_path)
        sheet_names = workbook.sheet_names()
        sheet_metas = []
        for name in sheet_names:
            sheet_name = name.encode("utf-8").strip()
            if sheet_name.startswith("_") or sheet_name.startswith("#") or sheet_name.startswith("Sheet"):
                continue

            if sheet_name in all_sheet_names:
                raise Exception("sheet name collision: %s - %s, %s" %
                                (sheet_name, xls_file_path, all_sheet_names[sheet_name]))
            all_sheet_names[sheet_name] = xls_file_path

            LOG_INFO("Parsing sheet: " + sheet_name)
            sheet = workbook.sheet_by_name(sheet_name)
            sheet_meta = parse_fields(sheet_name, sheet, tag)
            if sheet_meta is None:
                continue
            sheet_metas.append(sheet_meta)
        if len(sheet_metas) > 0:
            all_sheet_metas[xls_file_path] = sheet_metas

    return all_sheet_metas


def process_path(file_path, tag, output):
    all_sheet_metas = parse_xls_sheet_meta(file_path, tag)
    gen_proto(all_sheet_metas)
    gen_binary(all_sheet_metas)

    if "cs" in output:
        from codegen import protobuf_net_codegen
        LOG_INFO("==> Generating csharp binding")
        protobuf_net_codegen.gen_code(PACKAGE_NAME, LOADER_CLASS_NAME,
                                      DATA_BLOCKS_STRUCT_NAME, all_sheet_metas, CS_OUTPUT_PATH)

    LOG_INFO("*** DONE ***")


def usage():
    print '''
Usage: %s [options] excel_file output_dir
option:
    -h, --help
    -t, --tag=              Only export fields which has the tag
    -o, --output=cs,cpp     Generate cs,cpp bindings
        --loader_name=      Config loader class name
        --package_name=     Proto package name
''' % (sys.argv[0])


def init_output_paths(output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    global PROTO_OUTPUT_PATH
    global BYTES_OUTPUT_PATH
    global PYTHON_OUTPUT_PATH
    global CS_OUTPUT_PATH

    PROTO_OUTPUT_PATH = os.path.join(output_dir, "proto")
    BYTES_OUTPUT_PATH = os.path.join(output_dir, "bytes")
    PYTHON_OUTPUT_PATH = os.path.join(output_dir, "py")
    CS_OUTPUT_PATH = os.path.join(output_dir, "cs")

    os.makedirs(PROTO_OUTPUT_PATH)
    os.makedirs(PYTHON_OUTPUT_PATH)
    os.makedirs(BYTES_OUTPUT_PATH)


if __name__ == '__main__':
    try:
        opt, args = getopt.getopt(sys.argv[1:],
                                  "ht:o:", ["help", "output=", "tag=", "package_name=", "loader_name="])
    except getopt.GetoptError, err:
        print "err:", (err)
        usage()
        sys.exit(-1)

    if len(args) < 2:
        print "not enough arguments."
        usage()
        sys.exit(-1)

    xls_file_path = args[0]
    output_dir = args[1]

    output = []
    tag = None
    for op, value in opt:
        if op == "-h" or op == "--help":
            usage()
            sys.exit(0)
        elif op == "-t" or op == "--tag":
            tag = value
        elif op == "-o" or op == "--output":
            output = value.split(',')
        elif op == "--loader_name":
            # TODO: Check if it's a valid type name
            value = value.strip()
            if len(value) > 0:
                LOADER_CLASS_NAME = value
        elif op == "--package_name":
            # TODO: Check if it's a valid type name
            value = value.strip()
            if len(value) > 0:
                PACKAGE_NAME = value

    init_output_paths(output_dir)

    sys.path.append(PYTHON_OUTPUT_PATH)

    try:
        process_path(xls_file_path, tag, output)
    except BaseException, info:
        print info
        raise
