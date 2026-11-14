"""Canonical prerecorded speech: title + answer, and nothing else."""
def spoken_text(card):
    return (card.get('title') or card['path'][2]).strip() + '\n' + card['answer'].strip()
