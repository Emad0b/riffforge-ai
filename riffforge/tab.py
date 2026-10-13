"""Globally optimized monophonic fingering; string 1 is high E."""

TUNING = (40, 45, 50, 55, 59, 64)


def positions(pitch):
    return [
        (6 - i, pitch - open_pitch)
        for i, open_pitch in enumerate(TUNING)
        if 0 <= pitch - open_pitch <= 24
    ]


def movement(a, b):
    return abs(a[1] - b[1]) + 0.8 * abs(a[0] - b[0])


def assign(notes):
    if not notes:
        return []
    choices = [positions(n["pitch"]) for n in notes]
    if any(not c for c in choices):
        raise ValueError("Pitch outside standard-tuning 24-fret guitar range")
    costs = [[0.06 * f for _, f in choices[0]]]
    parents = [[]]
    for i in range(1, len(notes)):
        row, links = [], []
        for b in choices[i]:
            candidates = [
                costs[-1][j] + movement(a, b) + 0.06 * b[1]
                for j, a in enumerate(choices[i - 1])
            ]
            best = min(range(len(candidates)), key=candidates.__getitem__)
            row.append(candidates[best])
            links.append(best)
        costs.append(row)
        parents.append(links)
    selected = min(range(len(costs[-1])), key=costs[-1].__getitem__)
    path = []
    for i in reversed(range(len(notes))):
        string, fret = choices[i][selected]
        path.append({**notes[i], "string": string, "fret": fret})
        if i:
            selected = parents[i][selected]
    return path[::-1]


def dominant_line(raw):
    """Preserve raw polyphony separately; select strongest non-overlapping events."""
    selected = []
    for note in sorted(raw, key=lambda n: (n["start"], -n["confidence"])):
        if not positions(note["pitch"]):
            continue
        if selected and note["start"] < selected[-1]["end"] - 0.06:
            if (
                abs(note["start"] - selected[-1]["start"]) < 0.06
                and note["confidence"] > selected[-1]["confidence"]
            ):
                selected[-1] = note
            continue
        selected.append(note)
    return assign(selected)
