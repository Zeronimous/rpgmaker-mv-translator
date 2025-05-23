import json
import os
import argparse
import copy
import re

# Regex patterns to parse the unique_id
# For Map*.json: Map001_event1_page0_list0_param0 OR Map001_event1_page0_list1_param0_choice0
map_pattern_text = re.compile(r"^(Map\d+)_event(\d+)_page(\d+)_list(\d+)_param(\d+)$")
map_pattern_choice = re.compile(r"^(Map\d+)_event(\d+)_page(\d+)_list(\d+)_param(\d+)_choice(\d+)$")

# For CommonEvents.json: CommonEvents_event1_list0_param0 OR CommonEvents_event1_list1_param0_choice0
common_event_pattern_text = re.compile(r"^(CommonEvents)_event(\d+)_list(\d+)_param(\d+)$")
common_event_pattern_choice = re.compile(r"^(CommonEvents)_event(\d+)_list(\d+)_param(\d+)_choice(\d+)$")

def parse_id(unique_id):
    """Parses a unique_id string and returns a dictionary with its components."""
    match = map_pattern_choice.match(unique_id)
    if match:
        return {
            "type": "map_choice",
            "filename_base": match.group(1),
            "event_idx": int(match.group(2)),
            "page_idx": int(match.group(3)),
            "list_idx": int(match.group(4)),
            "param_idx": int(match.group(5)), # This is the index of the choices array within parameters
            "choice_idx": int(match.group(6)),
        }
    match = map_pattern_text.match(unique_id)
    if match:
        return {
            "type": "map_text",
            "filename_base": match.group(1),
            "event_idx": int(match.group(2)),
            "page_idx": int(match.group(3)),
            "list_idx": int(match.group(4)),
            "param_idx": int(match.group(5)), # This is the index of the text within parameters
        }
    match = common_event_pattern_choice.match(unique_id)
    if match:
        return {
            "type": "common_event_choice",
            "filename_base": match.group(1),
            "event_idx": int(match.group(2)),
            "list_idx": int(match.group(3)),
            "param_idx": int(match.group(4)), # Index of choices array
            "choice_idx": int(match.group(5)),
        }
    match = common_event_pattern_text.match(unique_id)
    if match:
        return {
            "type": "common_event_text",
            "filename_base": match.group(1),
            "event_idx": int(match.group(2)),
            "list_idx": int(match.group(3)),
            "param_idx": int(match.group(4)), # Index of text
        }
    return None

def main():
    parser = argparse.ArgumentParser(description="Injects translated text back into RPG Maker MV/MZ JSON files.")
    parser.add_argument("--translated_folder", required=True, help="Path to the folder containing translated .txt files.")
    parser.add_argument("--original_json_folder", required=True, help="Path to the folder containing original JSON files.")
    parser.add_argument("--output_json_folder", required=True, help="Path where the new JSON files with injected translations will be saved.")
    args = parser.parse_args()

    if not os.path.exists(args.output_json_folder):
        os.makedirs(args.output_json_folder)
        print(f"Created output folder: {args.output_json_folder}")

    for txt_filename in os.listdir(args.translated_folder):
        if not txt_filename.endswith(".txt"):
            continue

        translated_filepath = os.path.join(args.translated_folder, txt_filename)
        json_filename_base = os.path.splitext(txt_filename)[0]
        original_json_filename = f"{json_filename_base}.json"
        original_json_filepath = os.path.join(args.original_json_folder, original_json_filename)
        output_json_filepath = os.path.join(args.output_json_folder, original_json_filename)

        if not os.path.exists(original_json_filepath):
            print(f"Warning: Original JSON file {original_json_filepath} not found for {txt_filename}. Skipping.")
            continue

        print(f"Processing {txt_filename} -> {original_json_filename}")

        try:
            with open(original_json_filepath, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
        except Exception as e:
            print(f"Error loading original JSON {original_json_filepath}: {e}. Skipping.")
            continue
        
        modified_data = copy.deepcopy(original_data)

        try:
            with open(translated_filepath, 'r', encoding='utf-8') as f_translated:
                for line_num, line in enumerate(f_translated):
                    line = line.strip()
                    if not line:
                        continue # Skip empty lines

                    parts = line.split(":", 1)
                    if len(parts) != 2:
                        print(f"Warning: Malformed line {line_num+1} in {txt_filename}: '{line}'. Skipping.")
                        continue
                    
                    unique_id, translated_text = parts[0], parts[1]
                    parsed_components = parse_id(unique_id)

                    if not parsed_components:
                        print(f"Warning: Could not parse ID '{unique_id}' on line {line_num+1} in {txt_filename}. Skipping.")
                        continue
                    
                    try:
                        item_list = None # This will point to event_page['list'] or common_event['list']
                        target_parameters = None # This will point to item['parameters']
                        
                        if parsed_components["type"].startswith("map"):
                            event = modified_data["events"][parsed_components["event_idx"]]
                            if not event: continue # Skip if event is null
                            page = event["pages"][parsed_components["page_idx"]]
                            item_list = page["list"]
                            item = item_list[parsed_components["list_idx"]]
                            target_parameters = item["parameters"]

                            if parsed_components["type"] == "map_choice":
                                target_parameters[parsed_components["param_idx"]][parsed_components["choice_idx"]] = translated_text
                            else: # map_text
                                target_parameters[parsed_components["param_idx"]] = translated_text
                        
                        elif parsed_components["type"].startswith("common_event"):
                            event_like_object = modified_data[parsed_components["event_idx"]]
                            if not event_like_object: continue # Skip if event is null
                            item_list = event_like_object["list"]
                            item = item_list[parsed_components["list_idx"]]
                            target_parameters = item["parameters"]

                            if parsed_components["type"] == "common_event_choice":
                                target_parameters[parsed_components["param_idx"]][parsed_components["choice_idx"]] = translated_text
                            else: # common_event_text
                                target_parameters[parsed_components["param_idx"]] = translated_text
                                
                    except IndexError:
                        print(f"Warning: Index out of bounds for ID '{unique_id}' in {txt_filename}. Data structure might not match. Skipping this ID.")
                    except TypeError: # Handles cases like trying to index None (e.g. if an event is null)
                         print(f"Warning: Encountered None where an object/list was expected for ID '{unique_id}' in {txt_filename}. Skipping this ID.")
                    except Exception as e:
                        print(f"Warning: Unexpected error when processing ID '{unique_id}' in {txt_filename}: {e}. Skipping this ID.")

        except Exception as e:
            print(f"Error reading or processing translated file {translated_filepath}: {e}")
            continue

        try:
            with open(output_json_filepath, 'w', encoding='utf-8') as f_out:
                json.dump(modified_data, f_out, ensure_ascii=False, indent=4)
            print(f"Injected translations saved to {output_json_filepath}")
        except Exception as e:
            print(f"Error writing modified JSON to {output_json_filepath}: {e}")

if __name__ == "__main__":
    main()
