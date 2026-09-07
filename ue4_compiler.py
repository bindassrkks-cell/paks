import os
import json
import struct
import hashlib
import zlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_PAK_DIR = os.path.join(BASE_DIR, "original_pak")
EDITOR_DIR = os.path.join(BASE_DIR, "editor")
RESULT_DIR = os.path.join(BASE_DIR, "result")
CONFIG_PATH = os.path.join(BASE_DIR, "data.json")

PAK_MAGIC = 0x5A6F12E1

def init_folders():
    for f in [ORIGINAL_PAK_DIR, EDITOR_DIR, RESULT_DIR]:
        os.makedirs(f, exist_ok=True)

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def patch_binary_asset(file_path, config):
    with open(file_path, "rb") as f:
        data = bytearray(f.read())

    # 1. Headshot Multiplier (Arbitrary Float Support)
    if config.get("headshot", False):
        multiplier = float(config.get("headshot_multiplier", 3.5))
        f_bytes = struct.pack("<f", multiplier)
        marker = b"HeadshotMultiplier"
        if marker in data:
            pos = data.find(marker) + len(marker) + 4
            data[pos:pos+4] = f_bytes
        else:
            data.extend(b"\x00HeadshotMultiplier\x00\x00\x00\x00" + f_bytes)

    # 2. Magic Bullet / Bullet Tracking
    magic_val = float(config.get("magic_bt", 0.0))
    if magic_val > 0.0:
        magic_bytes = struct.pack("<f", magic_val)
        marker = b"BulletTrackRadius"
        if marker in data:
            pos = data.find(marker) + len(marker) + 4
            data[pos:pos+4] = magic_bytes
        else:
            data.extend(b"\x00BulletTrackRadius\x00\x00\x00\x00" + magic_bytes)

    # 3. Bullet Spread Compression
    spread = float(config.get("bullet_spread", 0.0))
    if spread > 0.0:
        spread_bytes = struct.pack("<f", 1.0 / spread)
        marker = b"BulletSpread"
        if marker in data:
            pos = data.find(marker) + len(marker) + 4
            data[pos:pos+4] = spread_bytes

    # 4. Weapons No Recoil
    recoil_settings = config.get("no_recoil", {})
    for gun, enabled in recoil_settings.items():
        if enabled:
            gun_b = gun.encode("ascii")
            if gun_b in data:
                pos = data.find(gun_b)
                data[pos:pos+len(gun_b)] = b"REC_" + gun_b[4:] if len(gun_b) >= 4 else gun_b

    # 5. Vehicle Speed
    car_cfg = config.get("car_speed", {})
    car_mult = float(car_cfg.get("multiplier", 1.0))
    if car_mult > 1.0:
        car_bytes = struct.pack("<f", car_mult)
        marker = b"MaxVehicleSpeed"
        if marker in data:
            pos = data.find(marker) + len(marker) + 4
            data[pos:pos+4] = car_bytes

    with open(file_path, "wb") as f:
        f.write(data)

def compile_pak():
    init_folders()
    config = load_config()

    # Step 1: Patch every asset in editor/
    patched_count = 0
    for root, _, files in os.walk(EDITOR_DIR):
        for file in files:
            if file.endswith((".uexp", ".uasset", ".ini", ".lua")):
                patch_binary_asset(os.path.join(root, file), config)
                patched_count += 1

    # Step 2: Target PAK Name
    orig_paks = [f for f in os.listdir(ORIGINAL_PAK_DIR) if f.endswith((".pak", ".obb"))]
    target_pak_name = orig_paks[0] if orig_paks else "game_patch_custom.pak"
    output_path = os.path.join(RESULT_DIR, target_pak_name)

    # Step 3: Authentic Unreal Engine PAK Build
    file_records = []
    curr_offset = 0

    with open(output_path, "wb") as pak_out:
        for root, _, files in os.walk(EDITOR_DIR):
            for file in files:
                f_path = os.path.join(root, file)
                rel_path = os.path.relpath(f_path, EDITOR_DIR).replace("\\", "/")

                with open(f_path, "rb") as f:
                    raw = f.read()

                uncomp_sz = len(raw)
                comp = zlib.compress(raw, level=6)

                if len(comp) < uncomp_sz:
                    method = 1
                    payload = comp
                else:
                    method = 0
                    payload = raw

                comp_sz = len(payload)
                sha = hashlib.sha1(payload).digest()

                pak_out.write(payload)

                file_records.append({
                    "name": rel_path,
                    "offset": curr_offset,
                    "size": comp_sz,
                    "uncompressed_size": uncomp_sz,
                    "method": method,
                    "sha1": sha
                })
                curr_offset += comp_sz

        # UE4 PAK Index Table
        index_start = curr_offset
        mount_point = b"../../../\x00"
        pak_out.write(struct.pack("<I", len(mount_point)))
        pak_out.write(mount_point)
        pak_out.write(struct.pack("<I", len(file_records)))

        for rec in file_records:
            name_b = rec["name"].encode("utf-8") + b"\x00"
            pak_out.write(struct.pack("<I", len(name_b)))
            pak_out.write(name_b)
            pak_out.write(struct.pack("<q", rec["offset"]))
            pak_out.write(struct.pack("<q", rec["size"]))
            pak_out.write(struct.pack("<q", rec["uncompressed_size"]))
            pak_out.write(struct.pack("<I", rec["method"]))
            pak_out.write(rec["sha1"])
            if rec["method"] != 0:
                pak_out.write(struct.pack("<I", 1))
                pak_out.write(struct.pack("<q", 0))
                pak_out.write(struct.pack("<q", rec["size"]))
            pak_out.write(b"\x00")
            pak_out.write(struct.pack("<I", 65536))

        index_sz = pak_out.tell() - index_start

        # Index SHA1 & FPakInfo Footer
        pak_out.seek(index_start)
        idx_sha = hashlib.sha1(pak_out.read(index_sz)).digest()

        pak_out.seek(0, os.SEEK_END)
        pak_out.write(b"\x00")
        pak_out.write(struct.pack("<I", PAK_MAGIC))
        pak_out.write(struct.pack("<i", 4))
        pak_out.write(struct.pack("<q", index_start))
        pak_out.write(struct.pack("<q", index_sz))
        pak_out.write(idx_sha)

    return {
        "status": "success",
        "patched_files": patched_count,
        "packed_files": len(file_records),
        "pak_name": target_pak_name,
        "size_bytes": os.path.getsize(output_path),
        "download_url": "/api/download"
    }
