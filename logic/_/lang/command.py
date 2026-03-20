"""TOOL --lang {audit,list}

Language and localization management.
"""

from logic._._ import EcoCommand


class LangCommand(EcoCommand):
    name = "lang"
    usage = "TOOL --lang {audit <code> | list}"

    def handle(self, args):
        parser = self.create_parser("Language management")
        sub = parser.add_subparsers(dest="lang_command")
        la = sub.add_parser("audit", help="Audit translation coverage")
        la.add_argument("code", help="Language code")
        la.add_argument("--force", action="store_true", help="Clear audit cache")
        la.add_argument("--turing", action="store_true", help="Scan Turing states")
        sub.add_parser("list", help="List supported languages")

        parsed = parser.parse_args(args)

        if parsed.lang_command == "audit":
            from interface.lang import audit_lang
            audit_lang(parsed.code, self.project_root,
                       force=parsed.force, turing=parsed.turing,
                       translation_func=self._)
        elif parsed.lang_command == "list":
            from interface.lang import list_languages
            list_languages(self.project_root, translation_func=self._)
        else:
            parser.print_help()
        return 0
