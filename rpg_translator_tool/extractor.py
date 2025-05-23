import json
import os
import argparse

def extract_text_from_map_json(data, json_filename_base):
    """Extracts text from Map*.json data."""
    extracted_lines = []
    if not data or "events" not in data or not data["events"]:
        return extracted_lines

    for event_idx, event in enumerate(data["events"]):
        if event is None:
            continue
        for page_idx, page in enumerate(event.get("pages", [])):
            for list_idx, item in enumerate(page.get("list", [])):
                if item is None:
                    continue
                
                code = item.get("code")
                parameters = item.get("parameters")

                if code == 401:
                    text = parameters[0] if parameters and len(parameters) > 0 else None
                    if text and text.strip(): # Skip empty or null text
                        line_id = f"{json_filename_base}_event{event_idx}_page{page_idx}_list{list_idx}_param0"
                        extracted_lines.append(f"{line_id}:{text}")
                elif code == 102:
                    choices = parameters[0] if parameters and len(parameters) > 0 else []
                    for choice_idx, choice in enumerate(choices):
                        if choice and choice.strip(): # Skip empty or null choices
                            choice_id = f"{json_filename_base}_event{event_idx}_page{page_idx}_list{list_idx}_param0_choice{choice_idx}"
                            extracted_lines.append(f"{choice_id}:{choice}")
                elif code == 402:
                    # For code 402, text is item['parameters'][1]
                    text = parameters[1] if parameters and len(parameters) > 1 else None
                    if text and text.strip(): # Skip empty or null text
                        line_id = f"{json_filename_base}_event{event_idx}_page{page_idx}_list{list_idx}_param1"
                        extracted_lines.append(f"{line_id}:{text}")
    return extracted_lines

def extract_text_from_common_events_json(data, json_filename_base):
    """Extracts text from CommonEvents.json data."""
    extracted_lines = []
    if not data:
        return extracted_lines

    for event_idx, event_like_object in enumerate(data):
        if event_like_object is None:
            continue
        for list_idx, item in enumerate(event_like_object.get("list", [])):
            if item is None:
                continue

            code = item.get("code")
            parameters = item.get("parameters")

            if code == 401:
                text = parameters[0] if parameters and len(parameters) > 0 else None
                if text and text.strip(): # Skip empty or null text
                    line_id = f"{json_filename_base}_event{event_idx}_list{list_idx}_param0"
                    extracted_lines.append(f"{line_id}:{text}")
            elif code == 102:
                choices = parameters[0] if parameters and len(parameters) > 0 else []
                for choice_idx, choice in enumerate(choices):
                    if choice and choice.strip(): # Skip empty or null choices
                        choice_id = f"{json_filename_base}_event{event_idx}_list{list_idx}_param0_choice{choice_idx}"
                        extracted_lines.append(f"{choice_id}:{choice}")
            elif code == 402:
                text = parameters[1] if parameters and len(parameters) > 1 else None
                if text and text.strip(): # Skip empty or null text
                    line_id = f"{json_filename_base}_event{event_idx}_list{list_idx}_param1"
                    extracted_lines.append(f"{line_id}:{text}")
    return extracted_lines

def main():
    parser = argparse.ArgumentParser(description="Extracts text from RPG Maker MV/MZ JSON files.")
    parser.add_argument("--input_folder", required=True, help="Path to the folder containing original JSON files.")
    parser.add_argument("--output_folder", required=True, help="Path where the extracted .txt files will be saved.")
    args = parser.parse_args()

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
        print(f"Created output folder: {args.output_folder}")

    for filename in os.listdir(args.input_folder):
        if not filename.endswith(".json"):
            continue

        input_filepath = os.path.join(args.input_folder, filename)
        json_filename_base = os.path.splitext(filename)[0]
        output_txt_filename = f"{json_filename_base}.txt"
        output_filepath = os.path.join(args.output_folder, output_txt_filename)

        extracted_lines = []
        try:
            with open(input_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON from {input_filepath}: {e}")
            continue

        print(f"Processing {filename}...")
        if filename.startswith("Map") and filename.endswith(".json"):
            extracted_lines = extract_text_from_map_json(data, json_filename_base)
        elif filename == "CommonEvents.json":
            extracted_lines = extract_text_from_common_events_json(data, json_filename_base)
        
        if extracted_lines:
            try:
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    for line in extracted_lines:
                        f.write(line + "\n")
                print(f"Extracted text to {output_filepath}")
            except Exception as e:
                print(f"Error writing to {output_filepath}: {e}")
        else:
            print(f"No text found to extract in {filename}, or file type not supported for text extraction.")


if __name__ == "__main__":
    main()
