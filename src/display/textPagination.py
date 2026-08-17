import textwrap


def paginateText(
    text,
    charactersPerLine=24,
    linesPerPage=6,
):
    """
    Split an answer into TFT-sized pages.
    """

    wrappedLines = []

    for paragraph in text.splitlines():

        paragraph = paragraph.strip()

        if not paragraph:

            wrappedLines.append("")
            continue

        lines = textwrap.wrap(
            paragraph,
            width=charactersPerLine,
            break_long_words=True,
            break_on_hyphens=False,
        )

        wrappedLines.extend(lines)

    if not wrappedLines:
        return [""]

    pages = []

    for index in range(
        0,
        len(wrappedLines),
        linesPerPage,
    ):

        pageLines = wrappedLines[
            index:index + linesPerPage
        ]

        pages.append(
            "\n".join(pageLines)
        )

    return pages