"""Download names are untrusted metadata, never paths."""
import re


def safe_name(name):
    basename = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    basename = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", basename).strip(" .")[:120]
    if not basename:
        return "file.bin"
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", basename.split(".")[0], re.I):
        basename = "_" + basename
    return basename
