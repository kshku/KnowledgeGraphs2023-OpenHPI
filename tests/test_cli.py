from knowledgegraphs2023_openhpi.main import build_parser


def test_parser_has_subcommands():
    parser = build_parser()
    args = parser.parse_args(["query", "--section", "2"])
    assert args.command == "query"
    assert args.section == 2


def test_parser_build_command():
    parser = build_parser()
    args = parser.parse_args(["build"])
    assert args.command == "build"
