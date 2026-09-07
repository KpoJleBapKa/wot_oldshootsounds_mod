import json
import re
import xml.etree.ElementTree as element_tree
from pathlib import Path


VALID_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def main():
    project_root = Path(__file__).resolve().parents[1]
    reference = project_root / "reference" / "9.13-Wot-gun-sounds-for-wot"
    sources = [
        reference / "Actor-Mixer Hierarchy" / "Default Work Unit.wwu",
        reference / "Events" / "Weapons.wwu",
        reference / "Game Parameters" / "Weapons.wwu",
        reference / "States" / "Common.wwu",
        reference / "Switches" / "Weapons.wwu",
    ]
    names = set()
    for source in sources:
        document = element_tree.parse(source)
        for element in document.iter():
            name = element.attrib.get("Name")
            if name and VALID_NAME.fullmatch(name):
                names.add(name)
    events = json.loads((project_root / "mapping" / "gun_events.json").read_text(encoding="utf-8"))
    names.update(event["event_name"] for event in events)
    names.update(f"{event['event_name']}_mod" for event in events)
    content = "\n".join(sorted(names, key=str.lower)) + "\n"
    for side in ("old", "current"):
        (project_root / "work" / "banks" / side / "wwnames.txt").write_text(content, encoding="utf-8")
    print(f"Wwise names: {len(names)}")


if __name__ == "__main__":
    main()
