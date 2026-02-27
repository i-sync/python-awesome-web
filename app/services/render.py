import markdown2

MARKDOWN_EXTRAS = ['code-friendly', 'fenced-code-blocks', 'highlightjs-lang', 'tables', 'break-on-newline']


def markdown_to_html(content):
    return markdown2.markdown(content, extras=MARKDOWN_EXTRAS).replace(
        '<table>', '<table class="ui celled table">'
    )
