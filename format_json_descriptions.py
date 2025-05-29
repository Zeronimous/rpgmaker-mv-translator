"""
Processes JSON files in an input directory to format 'description' fields,
wrapping long lines at a specified maximum length, preserving existing newlines.
"""
import json
import os
import argparse

def format_description(text: str, max_len: int = 50) -> str:
    """
    Formats a given text string by wrapping long lines.

    Existing newline characters in the input text are preserved. Each line
    resulting from the initial split by newline characters is then processed.
    If a line exceeds max_len, it's wrapped at the last space within
    max_len characters, or force-broken if no suitable space is found.

    Args:
        text (str): The input string to format.
        max_len (int): The maximum length for any single line in the output.
                       Defaults to 50.

    Returns:
        str: The formatted string with lines wrapped as needed.
    """
    final_lines = []
    # First, split the input by existing newline characters to process each original line.
    for original_segment in text.split('\n'): 
        
        # If the segment (an original line) is already within max_len, append it as is.
        if len(original_segment) <= max_len:
            final_lines.append(original_segment)
            continue # Move to the next original_segment

        # If the segment is longer than max_len, it needs wrapping.
        lines_for_this_original_segment = []
        current_processing_part = original_segment # This is the part of the segment we are currently trying to wrap.
        
        # Loop as long as the current part of the segment is longer than max_len.
        # This condition is guaranteed to be true for the first iteration due to the check above.
        while len(current_processing_part) > max_len: 
            # Look for a space to split at within the first (max_len + 1) characters.
            # Slicing up to max_len + 1 allows rfind to find a space at exactly max_len.
            slice_to_check = current_processing_part[:max_len + 1]
            split_at = slice_to_check.rfind(' ', 0, max_len + 1) # Find the last space in this slice.

            if split_at > 0: # If a space is found at a positive index (not the beginning).
                lines_for_this_original_segment.append(current_processing_part[:split_at])
                current_processing_part = current_processing_part[split_at+1:] # Move past the space for the next part.
            else: # No suitable space found (or space is at index 0), so force break the line at max_len.
                lines_for_this_original_segment.append(current_processing_part[:max_len])
                current_processing_part = current_processing_part[max_len:]
        
        # Add the final remaining part of the current_processing_part (might be shorter than max_len).
        if current_processing_part: 
             lines_for_this_original_segment.append(current_processing_part)
        
        final_lines.extend(lines_for_this_original_segment)
            
    return "\n".join(final_lines)

def process_json_data(data_node):
    """
    Recursively traverses a JSON data structure (dict or list) and applies
    the format_description function to string values associated with keys
    named "description".

    The modification is done in-place.

    Args:
        data_node (Union[dict, list]): The current node (dict or list)
                                       in the JSON structure to process.
    """
    if isinstance(data_node, dict):
        for key, value in data_node.items():
            if key == "description" and isinstance(value, str):
                data_node[key] = format_description(value)
            elif isinstance(value, (dict, list)):
                process_json_data(value)
    elif isinstance(data_node, list):
        for item in data_node:
            process_json_data(item)

def main():
    parser = argparse.ArgumentParser(description="Format JSON descriptions.")
    parser.add_argument('--input_folder', default="originales", help="Folder containing original JSON files")
    parser.add_argument('--output_folder', default="arreglados", help="Folder to save modified JSON files")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    os.makedirs(output_folder, exist_ok=True)

    # Restored main loop
    for filename in os.listdir(input_folder):
        if filename.endswith(".json"):
            input_file_path = os.path.join(input_folder, filename)
            output_file_path = os.path.join(output_folder, filename)

            # Print statement for processing files
            print(f"Processing {input_file_path} -> {output_file_path}")

            try:
                # Attempt to open and read the input JSON file
                try:
                    with open(input_file_path, 'r', encoding='utf-8-sig') as f:
                        # Attempt to decode JSON data
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON in file: {input_file_path}. Skipping.")
                            continue # Skip to the next file
                except IOError:
                    print(f"Error opening or reading file: {input_file_path}. Skipping.")
                    continue # Skip to the next file
                
                process_json_data(data) # Modify data in place

                # Attempt to open and write the output JSON file
                try:
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                except IOError:
                    print(f"Error writing to file: {output_file_path}. Skipping this file's output.")

            except Exception as e: # General catch-all for other unexpected errors during processing a file
                print(f"An unexpected error occurred while processing {input_file_path}: {e}. Skipping.")

# This block handles command-line argument parsing and orchestrates the script's main functionality.
if __name__ == '__main__':
    main()
