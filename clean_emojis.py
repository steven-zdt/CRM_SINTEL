import os
import re

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Common emojis used in the project
    replacements = {
        '⚠️': 'WARNING:',
        '✅': 'OK:',
        '🚀': 'START:',
        '🛡️': 'SHIELD:',
        '📋': 'INFO:',
        '⏳': 'WAIT:',
        '🔄': 'SYNC:',
        '🏢': 'TENANT:',
        '🌐': 'GLOBAL:',
        '📦': 'STATIC:',
        '🔧': 'CONFIG:',
        '🛡': 'SHIELD:', # Alternative without variant selector
    }
    
    new_content = content
    for emoji, replacement in replacements.items():
        new_content = new_content.replace(emoji, replacement)
    
    # Remove any other non-ASCII characters that aren't common Spanish characters
    # Allowed: a-z, A-Z, 0-9, punctuation, áéíóúñÁÉÍÓÚÑ
    # regex for non-allowed: [^\x00-\x7fáéíóúñÁÉÍÓÚÑ¡¿]
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    base_dir = r'c:\Users\Administrator\Documents\crm_sintel\apps\tenant\contabilidad'
    count = 0
    for root, dirs, files in os.walk(base_dir):
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if clean_file(path):
                    print(f"Cleaned: {path}")
                    count += 1
    print(f"Total files cleaned: {count}")

if __name__ == '__main__':
    main()
