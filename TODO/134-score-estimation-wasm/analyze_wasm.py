import struct

def read_leb128(data, pos):
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos

def analyze_wasm(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    if data[:4] != b'\0asm':
        print("Not a valid WASM file")
        return

    pos = 8 # Skip magic and version
    
    print(f"WASM File: {file_path}")
    print(f"Size: {len(data)} bytes")
    
    while pos < len(data):
        section_id = data[pos]
        pos += 1
        section_len, pos = read_leb128(data, pos)
        section_end = pos + section_len
        
        if section_id == 7: # Export section
            num_exports, pos = read_leb128(data, pos)
            print(f"\nExports ({num_exports}):")
            for _ in range(num_exports):
                name_len, pos = read_leb128(data, pos)
                name = data[pos:pos+name_len].decode('utf-8')
                pos += name_len
                export_kind = data[pos]
                pos += 1
                export_index, pos = read_leb128(data, pos)
                kind_str = {0: "Function", 1: "Table", 2: "Memory", 3: "Global"}.get(export_kind, "Unknown")
                print(f"  - {name} ({kind_str} index {export_index})")
        else:
            pos = section_end

if __name__ == "__main__":
    analyze_wasm("OGSScoreEstimator.wasm")
