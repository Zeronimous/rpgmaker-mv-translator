import json
import os
import argparse
import re

def calculate_effective_length(text: str) -> int:
    """
    Calculates the "visible" or "countable" length of a given text string,
    considering RPG Maker control codes.
    """
    processed_text = text
    # Remove color codes \C[n] or \c[n]
    processed_text = re.sub(r'\\[Cc]\[\d+\]', '', processed_text)
    # Remove actor name codes \N[n] or \n[n]
    processed_text = re.sub(r'\\[Nn]\[\d+\]', '', processed_text)
    # Remove pause codes \.
    processed_text = re.sub(r'\\\.','', processed_text) # \. needs to be escaped in regex
    # Replace variable codes \V[n] or \v[n] with "XX"
    processed_text = re.sub(r'\\[Vv]\[\d+\]', 'XX', processed_text)
    return len(processed_text)

def format_rpg_text(original_text: str, max_len: int = 50) -> str:
    """
    Formats RPG Maker text by wrapping lines to a maximum effective length,
    handling control codes correctly. Relies on calculate_effective_length.
    """
    # Step 1: Check if formatting is needed
    if calculate_effective_length(original_text) <= max_len:
        return original_text

    # Step 2: Initialize result_lines
    result_lines = []
    # Step 3: Set text_to_process
    text_to_process = original_text
    
    # Regex to find control codes or single characters. DOTALL is NOT used.
    unit_regex = r'(\\[CcVv]\[\d+\]|\\\.|.)'

    # Step 4: Main loop
    while calculate_effective_length(text_to_process) > max_len:
        # Step 4.a, 4.b: Initialize for current line build attempt
        current_line_original_chars = "" 
        current_line_effective_length = 0
        
        # Step 4.c, 4.d: Initialize break points for current text_to_process
        last_space_break_point = -1  # Index *of* the space in text_to_process
        force_break_point = -1       # Index in text_to_process to break *at* or *after*
        
        # Step 4.e: Iterate through units to determine one line (Revised Logic from prompt)
        for match_obj in re.finditer(unit_regex, text_to_process): # No re.DOTALL
            unit = match_obj.group(0)
            unit_effective_len = calculate_effective_length(unit)

            # Check if adding this unit would overflow an already started line
            if current_line_effective_length + unit_effective_len > max_len and \
               current_line_original_chars != "": # Line has content, this unit overflows
                force_break_point = match_obj.start() # Break *before* this unit
                break # Exit unit iteration
            
            # Tentatively add unit
            current_line_original_chars += unit
            current_line_effective_length += unit_effective_len

            if unit == ' ':
                last_space_break_point = match_obj.start() # The index of the space character itself
            
            # Check if line is now too long or a perfect fit
            if current_line_effective_length >= max_len: # Reached or exceeded max_len with this unit
                force_break_point = match_obj.end() # Break *after* this unit
                break # Exit unit iteration
        
        # If inner loop finished without an explicit break (force_break_point not set by overflow/exact fit)
        if force_break_point == -1:
            # This means all units in text_to_process were processed without exceeding max_len for the current line attempt
            force_break_point = len(text_to_process) # All remaining text forms the line or fits

        line_to_add = ""
        
        # Step 4.f: Check for space break
        # A space break is valid if a space was found (last_space_break_point != -1)
        # AND this space occurs strictly before the force_break_point.
        # (force_break_point could be len(text_to_process) if all remaining text fits)
        if last_space_break_point != -1 and \
           last_space_break_point < force_break_point:
            line_to_add = text_to_process[:last_space_break_point] # Text before the space
            text_to_process = text_to_process[last_space_break_point+1:] # Text after the space, skipping the space
        
        # Step 4.g: Else if no suitable space break was used, use force_break_point
        elif force_break_point != -1: # force_break_point was determined by unit loop
            line_to_add = text_to_process[:force_break_point]
            text_to_process = text_to_process[force_break_point:]
        
        # Step 4.h: Else (neither space break nor force break was applicable from unit loop)
        # This implies the whole text_to_process fits or is shorter than max_len (handled by outer loop)
        # or that the text_to_process is unprocessable by the unit loop (e.g. empty)
        else: 
            line_to_add = text_to_process
            text_to_process = ""


        # Step 4.i: Add the determined line
        result_lines.append(line_to_add)

        # Step 4.j: Safety break for no progress
        if len(line_to_add) == 0 and len(text_to_process) > 0 :
            # This implies that despite text_to_process having content, no line_to_add could be formed.
            print(f"Warning: No progress in format_rpg_text, appending remainder. Original: '{original_text}', Problematic Remainder: '{text_to_process}'")
            result_lines.append(text_to_process) 
            text_to_process = "" # Ensure loop terminates
            break 
    
    # Step 5: Add any final remaining part of text_to_process
    if len(text_to_process) > 0 : # Add if any characters remain
        result_lines.append(text_to_process)
    
    # Step 6: Return joined lines
    return "\n".join(result_lines)

def process_map_json_data(data: dict):
    """
    Traverses the JSON data structure of an RPG Maker Map file to find and
    format text in specified event command parameters using format_rpg_text.

    Modifies the input 'data' dictionary in-place.

    Args:
        data (dict): The loaded JSON data from a MapXXX.json file.
    """
    if not isinstance(data, dict) or "events" not in data or not isinstance(data["events"], list):
        # print("Warning: 'events' key missing or not a list in map data. Skipping.")
        return

    for event_item in data["events"]:
        if event_item is None: # Skip null events (often happens for deleted events)
            continue
        if not isinstance(event_item, dict) or "pages" not in event_item or \
           not isinstance(event_item["pages"], list):
            # print(f"Warning: Event item {event_item.get('id', '')} has missing/invalid 'pages'. Skipping.")
            continue

        for page_item in event_item["pages"]:
            if not isinstance(page_item, dict) or "list" not in page_item or \
               not isinstance(page_item["list"], list):
                # print(f"Warning: Page in event {event_item.get('id', '')} has missing/invalid command 'list'. Skipping.")
                continue
            
            for command_item in page_item["list"]:
                if not isinstance(command_item, dict) or "code" not in command_item or \
                   "parameters" not in command_item or not isinstance(command_item["parameters"], list):
                    # print(f"Warning: Command item in event {event_item.get('id', '')} is invalid. Skipping: {command_item}")
                    continue

                # Handle Code 401 (Text)
                if command_item['code'] == 401:
                    if len(command_item['parameters']) > 0 and \
                       isinstance(command_item['parameters'][0], str):
                        command_item['parameters'][0] = format_rpg_text(command_item['parameters'][0])
                
                # Handle Code 402 (Choice Option - when an answer is selected in Show Choice)
                # This code appears *after* a Show Choice command, defining the branch for that choice.
                # The text of the choice itself is part of the 102 command.
                # Code 402, parameter 1 is the string of the choice that this branch corresponds to.
                elif command_item['code'] == 402:
                     if len(command_item['parameters']) > 1 and \
                        isinstance(command_item['parameters'][1], str):
                         command_item['parameters'][1] = format_rpg_text(command_item['parameters'][1])

                # Handle Code 102 (Show Choices)
                elif command_item['code'] == 102:
                    if len(command_item['parameters']) > 0 and \
                       isinstance(command_item['parameters'][0], list):
                        original_choices = command_item['parameters'][0]
                        formatted_choices = []
                        for choice_text in original_choices:
                            if isinstance(choice_text, str):
                                formatted_choices.append(format_rpg_text(choice_text))
                            else:
                                formatted_choices.append(choice_text) # Preserve non-string items
                        command_item['parameters'][0] = formatted_choices
                
                # Note: Code 108 (Conditional Branch - Text in comment form) is not handled here yet.
                # It would be command_item['parameters'][0] if it's a comment.
                # However, these are usually not player-facing dialogue.

def main():
    parser = argparse.ArgumentParser(description="Format MapXXX.json dialogue files.")
    parser.add_argument('--input_folder', default="originales", help="Folder containing original MapXXX.json files")
    parser.add_argument('--output_folder', default="arreglados_maps", help="Folder to save modified MapXXX.json files")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        # Step 1: Filter for Map Files
        if filename.startswith("Map") and filename.lower().endswith(".json"):
            input_file_path = os.path.join(input_folder, filename)
            output_file_path = os.path.join(output_folder, filename)
            
            print(f"Processing Map file: {input_file_path} -> {output_file_path}")

            try:
                with open(input_file_path, 'r', encoding='utf-8-sig') as f:
                    map_data = json.load(f)
                
                # Step 2: Call Processing Function
                process_map_json_data(map_data) # This function modifies map_data in-place
                
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(map_data, f, indent=4, ensure_ascii=False)
                
                print(f"Successfully processed and saved: {output_file_path}")

            except json.JSONDecodeError:
                print(f"Error decoding JSON in file: {input_file_path}. Skipping.")
            except IOError: # Catching generic IOError for open/read/write issues
                print(f"Error opening, reading or writing file: {input_file_path} or {output_file_path}. Skipping.")
            except Exception as e: # Catch-all for other unexpected errors
                print(f"An unexpected error occurred with file {input_file_path}: {e}. Skipping.")
        else:
            # Optional: print(f"Skipping non-Map file: {filename}")
            pass

if __name__ == '__main__':
    main()
