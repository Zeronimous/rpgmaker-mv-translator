import deepl
import argparse
import os
import time

DEEPL_API_KEY = "YOUR_DEEPL_API_KEY_HERE" # IMPORTANT: Replace with your DeepL API Key

def try_translate_sentence(translator, text, source_lang_code, dest_lang_code, max_retries=5):
    """
    Tries to translate a sentence using the provided translator.
    Includes retry logic and case adjustment.
    Returns (translated_text, success_flag).
    """
    target = text # Store original text for case adjustment comparison
    if not text.strip(): # If text is empty or whitespace only
        return text, True # Return original text, consider it "successful" as no translation needed

    for attempt in range(max_retries):
        try:
            result = translator.translate_text(text, source_lang=source_lang_code, target_lang=dest_lang_code)
            translated_text = result.text

            # Case adjustment
            if target and target[0].isalpha() and \
               translated_text and translated_text[0].isalpha() and \
               not target[0].isupper() and translated_text[0].isupper():
                translated_text = translated_text[0].lower() + translated_text[1:]
            
            return translated_text, True
        except deepl.DeepLException as e:
            print(f"DeepL API Exception: {e}. Retrying ({attempt + 1}/{max_retries})...")
            if "Access denied" in str(e) or "Authorization" in str(e) or "403" in str(e):
                print("API key seems invalid. Further retries for this text will likely fail.")
                return text, False # No point retrying if key is bad
            time.sleep(1)
        except Exception as e: # Catching other potential network errors, though DeepLException should cover most
            print(f"An unexpected error occurred during translation: {e}. Retrying ({attempt + 1}/{max_retries})...")
            time.sleep(1)
            
    return text, False # Return original text if all retries fail

def main():
    parser = argparse.ArgumentParser(description="Translates text files using DeepL API.")
    parser.add_argument("--input_folder", required=True, help="Path to the folder containing .txt files from extractor.py.")
    parser.add_argument("--output_folder", required=True, help="Path where the translated .txt files will be saved.")
    parser.add_argument("--source_lang", default='EN', help="Source language code (e.g., 'EN').")
    parser.add_argument("--dest_lang", default='ES', help="Destination language code (e.g., 'ES').")
    args = parser.parse_args()

    if DEEPL_API_KEY == "YOUR_DEEPL_API_KEY_HERE":
        print("Warning: DeepL API Key is set to the placeholder. Please replace it with your actual key in the script for real translations.")

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
        print(f"Created output folder: {args.output_folder}")

    try:
        translator = deepl.Translator(DEEPL_API_KEY)
        # Test API authentication, this will raise an exception if the key is invalid
        # We'll try to get usage to see if the key is valid, without translating anything yet
        try:
            usage = translator.get_usage()
            print(f"DeepL API usage: {usage.character.count}/{usage.character.limit} characters used.")
        except deepl.DeepLException as e:
            if "Access denied" in str(e) or "Authorization" in str(e) or "403" in str(e):
                 print(f"Warning: DeepL API Key seems invalid or lacks permissions: {e}. Translations will likely fail and return original text.")
            else:
                print(f"Warning: Could not verify DeepL API Key, an error occurred: {e}. Translations may fail.")

    except Exception as e: # Catch error during Translator initialization
        print(f"Error initializing DeepL Translator: {e}. Ensure the API key is valid and the 'deepl' library is installed correctly.")
        print("Translations will use original text.")
        translator = None # Set translator to None so try_translate_sentence can handle it

    for filename in os.listdir(args.input_folder):
        if not filename.endswith(".txt"):
            continue

        input_filepath = os.path.join(args.input_folder, filename)
        output_filepath = os.path.join(args.output_folder, filename) # Output filename is the same

        print(f"Processing {filename}...")
        
        translated_lines = []
        try:
            with open(input_filepath, 'r', encoding='utf-8') as f_in:
                for line_number, line in enumerate(f_in):
                    line = line.strip() # Remove trailing newline
                    if not line: # Skip empty lines in the input file
                        translated_lines.append("")
                        continue

                    parts = line.split(":", 1)
                    if len(parts) != 2:
                        print(f"Warning: Malformed line {line_number+1} in {filename}: '{line}'. Skipping.")
                        translated_lines.append(line) # Write malformed line as is
                        continue
                    
                    unique_id, text_to_translate = parts[0], parts[1]

                    if not text_to_translate.strip(): # Handle lines like "ID:" (empty text)
                        translated_lines.append(f"{unique_id}:")
                        continue
                    
                    if translator:
                        translated_text, success = try_translate_sentence(translator, text_to_translate, args.source_lang, args.dest_lang)
                        if not success:
                            print(f"Warning: Failed to translate text with ID {unique_id}: '{text_to_translate}'. Original text used.")
                        translated_lines.append(f"{unique_id}:{translated_text}")
                    else: # If translator initialization failed
                        print(f"Warning: Translator not available. Using original text for ID {unique_id}.")
                        translated_lines.append(f"{unique_id}:{text_to_translate}")

        except Exception as e:
            print(f"Error processing file {input_filepath}: {e}")
            continue # Move to next file if one file has a major read error

        try:
            with open(output_filepath, 'w', encoding='utf-8') as f_out:
                for t_line in translated_lines:
                    f_out.write(t_line + "\n")
            print(f"Translated text saved to {output_filepath}")
        except Exception as e:
            print(f"Error writing to {output_filepath}: {e}")

if __name__ == "__main__":
    main()
