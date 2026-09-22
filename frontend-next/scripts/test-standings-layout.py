"""Check the real standings markup against the complete global CSS cascade.

Run after npm ci with: python scripts/test-standings-layout.py
Requires: pip install cssselect2 tinycss2 lxml
Use --baseline to demonstrate the regression against the checkout's HEAD CSS.
This checks selector precedence, not browser painting or text measurements.
"""

import re
import subprocess
import sys
from pathlib import Path

import cssselect2
import tinycss2
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "--baseline" in sys.argv


def source(path):
    if BASELINE:
        return subprocess.check_output(
            ["git", "show", f"HEAD:frontend-next/{path}"], cwd=ROOT, text=True
        )
    return (ROOT / path).read_text()


markup = subprocess.check_output(["node", "-e", r"""
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const code = ts.transpileModule(fs.readFileSync('src/components/TextTvStandings.tsx','utf8'),
  {compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const exports = {};
vm.runInNewContext(code,{exports,require});
process.stdout.write(renderToStaticMarkup(React.createElement(exports.TextTvStandings,{
  name:'B', rows:[{position:1,team_id:1,Lag:'Premium Barcelona',S:12,V:8,O:3,F:1,MS:'+24',P:27}]
})));
"""], cwd=ROOT, text=True)

document = html.document_fromstring(
    '<div class="view-mode-switch is-public"><a>Rapportering</a><a>Admin</a></div>'
    '<main class="page-shell page-shell--matchday page-shell--public-v3">'
    f'<div class="table-stack">{markup}</div></main>'
)
root = cssselect2.ElementWrapper.from_html_root(document)
assert document.xpath("//tbody/tr/td//text()") == ["1", "Premium Barcelona", "12", "8", "3", "1", "+24", "27"]

css = "\n".join(source("src/app/" + name) for name in
                re.findall(r'import "\./([^"\n]+\.css)"', source("src/app/layout.tsx")))


def active_rules(rules, width):
    for rule in rules:
        if rule.type == "qualified-rule":
            yield rule
        elif rule.type == "at-rule" and rule.lower_at_keyword == "media":
            query = tinycss2.serialize(rule.prelude)
            bounds = re.findall(r"(min|max)-width\s*:\s*([\d.]+)px", query)
            if all(width >= float(n) if kind == "min" else width <= float(n) for kind, n in bounds):
                yield from active_rules(tinycss2.parse_rule_list(rule.content), width)


def cascade(width):
    matcher = cssselect2.Matcher()
    for rule in active_rules(tinycss2.parse_stylesheet(css), width):
        declarations = [d for d in tinycss2.parse_declaration_list(rule.content) if d.type == "declaration"]
        # Vendor pseudo-elements cannot affect the element boxes under test.
        selector_text = re.sub(r"::-(?:webkit|moz)-[\w-]+", "::before", tinycss2.serialize(rule.prelude))
        for selector in cssselect2.compile_selector_list(selector_text):
            matcher.add_selector(selector, declarations)

    def style(element):
        winners = {}
        for specificity, order, pseudo, declarations in matcher.match(element):
            if pseudo:
                continue
            for index, declaration in enumerate(declarations):
                priority = (declaration.important, specificity, order, index)
                if declaration.name not in winners or priority >= winners[declaration.name][0]:
                    winners[declaration.name] = (priority, tinycss2.serialize(declaration.value).strip())
        return {name: value for name, (_, value) in winners.items()}
    return style


for width in [320, 360, 390, 700, 760, 1024]:
    computed = cascade(width)
    for cell in root.query_all(".texttv--standings th, .texttv--standings td"):
        assert computed(cell).get("display", "table-cell") == "table-cell", (width, cell.etree_element.text, "hidden column")
    assert computed(root.query(".view-mode-switch")).get("position") == "relative", (width, "floating shortcuts")
    if width <= 760:
        table = computed(root.query(".texttv--standings table"))
        assert table["min-width"] == "0", (width, table)
        assert table["width"] == "100%", (width, table)
    if width <= 700:
        assert computed(root.query(".standings-team-name"))["white-space"] == "normal"
    print(f"PASS {width}px: all eight columns, values and shortcut positioning")
