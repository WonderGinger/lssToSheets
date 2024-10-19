#!/usr/bin/python3
from sys import maxsize
import xml.etree.ElementTree as ET
import re
import os
import argparse
from datetime import timedelta

regex = re.compile(r'((?P<hours>\d+?):)?((?P<minutes>\d+?):)?((?P<seconds>(\d+.?\d+)?)$)?')
pp = False

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return timedelta(0)
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = float(param)
    return timedelta(**time_params)

def segment_is_subsplit(name):
    if name is None:
        return 0
    return string_is_subsplit(name.text)

def string_is_subsplit(name_str):
    return '-' == name_str[0]

def extract_name_from_str(str):
    if string_is_subsplit(str):
        return str[1:]
    extract_name = re.compile(r'\{?([\w\s]+)\}?')
    match = extract_name.match(str)
    if match:
        return match.group(1)
    return None

def find_best_chapters(lss):
    tree = ET.parse(lss)
    root = tree.getroot()

    segments = root.find("Segments")
    if segments is None:
        return 1

    split_list = []
    subsplits = []
    golds = {}
    best_id_dict = {}

    for segment in segments:
        subsplits.append(segment)
        if not segment_is_subsplit(segment.find("Name")):
            split_list.append(subsplits)
            subsplits = []

    for split in split_list:
        split_name = ''
        best = maxsize
        if len(split) > 1:
            name_res = re.search('^{(?P<name>.*)}',split[-1].find("Name").text)
            if name_res is not None:
                split_name = name_res.groupdict()['name']
            else:
                split_name = split[-1].find("Name").text
            time_dict = {}
            for subsplit in split:
                segment_history = subsplit.find("SegmentHistory")
                for time in segment_history.findall("Time"):
                    game_time = time.find("GameTime")
                    if game_time is None:
                        continue
                    id = time.get("id")
                    time_str = game_time.text

                    time_f = round(parse_time(time_str).total_seconds(), 3)
                    if 0 == time_f:
                        print(id, time_str, game_time)
                        return 1

                    if id in time_dict:
                        time_dict[id].append(time_f)
                    else:
                        time_dict[id] = [time_f]
            times = []
            for id in time_dict:
                if len(time_dict[id]) == len(split):
                    times.append(sum(time_dict[id]))
                    sum_id = sum(time_dict[id])
                    if sum_id < best:
                        best_id_dict[split_name] = id
                        best = sum_id
            best = timedelta(seconds = min(times))
        else:
            split_name = split[0].find("Name").text
            best = parse_time(split[0].find("BestSegmentTime").find("GameTime").text)

        golds[split_name] = best

    output_str_list = []
    output_str_list.append("chapter,time")

    for name in golds:
        gold_row = name + "," + str(golds[name])
        output_str_list.append(gold_row)

    sob = timedelta(seconds = sum([golds[name].total_seconds() for name in golds]))
    sum_str = "sum," + str(sob)
    output_str_list.append(sum_str)

    out_filename = os.path.splitext(lss)[0] + '_chapters.txt'
    with open(out_filename, 'w') as f:
        f.write('\n'.join(output_str_list))

    if pp:
        print_table(output_str_list)
    else:
        print('\n'.join(output_str_list))

    print()
    find_best_chapters_subsplits(split_list, best_id_dict)


def find_best_chapters_subsplits(split_list, best_id_dict):
    chapter_gold_subsplits = {}
    for split in split_list:
        if len(split) > 1:
            name_res = re.search('^{(?P<name>.*)}',split[-1].find("Name").text)
            if name_res is not None:
                split_name = name_res.groupdict()['name']
            else:
                split_name = split[-1].find("Name").text
            for subsplit in split:
                subsplit_name = subsplit.find("Name").text
                segment_history = subsplit.find("SegmentHistory")
                for time in segment_history.findall("Time"):
                    game_time = time.find("GameTime")
                    if game_time is None:
                        continue

                    id = time.get("id")
                    if best_id_dict[split_name] != id:
                        continue

                    time_str = game_time.text
                    time_f = round(parse_time(time_str).total_seconds(), 3)
                    if 0 == time_f:
                        return 1
                    ele = (subsplit_name,time_f)
                    if split_name in chapter_gold_subsplits:
                        chapter_gold_subsplits[split_name].append(ele)
                    else:
                        chapter_gold_subsplits[split_name] = [ele]

    output_str_list = []

    if pp:
        output_str_list = []
        output_list = []
        max_len = 0

        for chapter in chapter_gold_subsplits:
            name_list = list(map(lambda x: x[0], chapter_gold_subsplits[chapter]))
            time_list = list(map(lambda x: str(x[1]), chapter_gold_subsplits[chapter]))
            time_list_f = list(map(lambda x: x[1], chapter_gold_subsplits[chapter]))

            header_str_list = [chapter]
            header_str_list.extend(name_list)

            subsplit_str_list = [str(timedelta(seconds=sum(time_list_f)))]
            subsplit_str_list.extend(time_list)

            max_len = max(len(header_str_list), max_len)

            output_list.append(header_str_list)
            output_list.append(subsplit_str_list)

        for s in output_list:
            if len(s) < max_len:
                s.extend([','] * (max_len - len(s) - 1))

        output_str_list = list(map(lambda x: ','.join(x), output_list))
        print_table(output_str_list, row_sep='-', row_sep_interval=2)

    else:
        for chapter in chapter_gold_subsplits:
            output_str_list.append(chapter + ',' + ','.join(map(lambda x: str(timedelta(seconds=x[1])), chapter_gold_subsplits[chapter])))
        print('\n'.join(output_str_list))



def find_best_checkpoints(lss):
    tree = ET.parse(lss)
    root = tree.getroot()

    segments = root.find("Segments")
    if segments is None:
        return 1

    split_names = []
    pb = {}
    golds = {}

    for segment in segments:
        name = segment.find("Name")
        split_times = segment.find("SplitTimes")
        if split_times is None or name is None:
            continue

        split_name = str(name.text)
        pb_split = split_times.find("SplitTime")
        if pb_split:
            pb_split = pb_split.find("GameTime")
        if pb_split:
            pb_split = parse_time(pb_split.text)

        gold_split = segment.find("BestSegmentTime")
        if gold_split:
            gold_split = gold_split.find("GameTime")
        if gold_split:
            gold_split = parse_time(gold_split.text)

        # if segment_is_subsplit(name):
        #     name = split_name[1:]
        # else:
        #     name = extract_name_from_str(split_name)
        #     if name in split_names:
                    
        split_names.append(split_name)
        golds[split_name] = gold_split
        pb[split_name] = pb_split


    best_split_times = find_best_split_times(lss)
    if not isinstance(best_split_times, dict):
        return 0
    output_str_list = []
    output_str_list.append("Checkpoint,Golds,PB Split Times,Best Split Times")
    for cp in split_names:
        output_str_list.append(f"{cp},{golds[cp].text},{pb[cp].text},{str(timedelta(seconds=best_split_times[cp]))}")

    out_filename = os.path.splitext(lss)[0] + '_checkpoints.txt'
    with open(out_filename, 'w') as f:
        f.write('\n'.join(output_str_list))
        if pp:
            print_table(output_str_list)
        else:
            print('\n'.join(output_str_list))

def find_best_split_times(lss):
    tree = ET.parse(lss)
    root = tree.getroot()

    segments = root.find("Segments")
    if segments is None:
        return 1

    best_split_times = {}
    time_dict = {}
    segment_names = []
    for segment in segments:
        name = segment.find("Name")
        if name is None:
            continue
        segment_names.append(name.text)

        segment_history = segment.find("SegmentHistory")
        if segment_history is None:
            continue
        for time in segment_history.findall("Time"):
            game_time = time.find("GameTime")
            if game_time is None:
                continue
            id = time.get("id")
            time_str = game_time.text

            time_f = round(parse_time(time_str).total_seconds(), 3)
            if 0 == time_f:
                print(id, time_str, game_time)
                return 1

            if id in time_dict:
                time_dict[id].append(time_dict[id][-1] + time_f)
            else:
                time_dict[id] = [time_f]

    for id in time_dict:
        time_list = time_dict[id]
        for ii, time in enumerate(time_list):
            found_best_exit = False
            if segment_names[ii] in best_split_times:
                if time < best_split_times[segment_names[ii]]:
                    found_best_exit = True
            else:
                found_best_exit = True

            if found_best_exit:
                best_split_times[segment_names[ii]] = time
    return best_split_times

def find_best_exits(lss):
    best_split_times = find_best_split_times(lss)
    if not isinstance(best_split_times, dict):
        return 0

    best_exits = {extract_name_from_str(k):str(timedelta(seconds=v)) for k, v in best_split_times.items() if not string_is_subsplit(k)}
    output_str_list = []
    for chapter in best_exits:
        output_str_list.append(str(chapter) + ',' + best_exits[chapter])

    out_filename = os.path.splitext(lss)[0] + '_best_exits.txt'
    with open(out_filename, 'w') as f:
        f.write('\n'.join(output_str_list))
        if pp:
            print_table(output_str_list)
        else:
            print('\n'.join(output_str_list))

def print_table(rows, row_sep=None, row_sep_interval=1, padding=2):
    col_cnt = str.count(rows[0], ',') + 1
    max_col_w = [0] * col_cnt
    token_list_2d = []
    for ii, line in enumerate(rows):
        tokens = str.split(line, ',')
        token_list_2d.append(tokens)
        for ii, t in enumerate(tokens):
            max_col_w[ii] = max(len(t) + padding, max_col_w[ii])

    line_count = 0
    for row in token_list_2d:
        if (row_sep is not None) and (line_count == row_sep_interval):
            if '\n' == row_sep:
                print()
            print(str(row_sep * sum(max_col_w)))
            line_count = 0
        line_count += 1

        for ii, token in enumerate(row):
            print(token , end='')
            print(' ' * (max_col_w[ii] - len(token)), end='')
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('lss', action='store', help='path to .lss file')
    parser.add_argument('-pretty', action='store_true', help='pretty print the values')
    args = parser.parse_args()

    if args.pretty:
        pp = True

    print(args.lss)

    print()
    print("Best Checkpoints")
    find_best_checkpoints(args.lss)

    print()
    print("Best Chapters")
    find_best_chapters(args.lss)

    print()
    print("Best Exits")
    find_best_exits(args.lss)
