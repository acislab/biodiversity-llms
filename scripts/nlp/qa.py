# Submit questions to GPT 3.5.
#
# Usage:
#  echo [TSV lines] | python qa.py [question]
#
# Plug in field values using the field name, e.g. "Who is {name}?"
# e.g. echo -e "species\tlocation\nAcer saccharum\tArkansas" | python qa.py "Does {species} naturally occur in {location}? Yes or no"

import argparse
import sys

from models.openai import GPT
import util

MODELS = {
    "gpt-3.5-turbo-0613": lambda args: GPT("gpt-3.5-turbo-0613", args.timeout, args.top_p),
    "gpt-4-1106-preview": lambda args: GPT("gpt-4-1106-preview", args.timeout, args.top_p),
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Submit questions to GPT 3.5 turbo")
    parser.add_argument("patterns", nargs="+")
    parser.add_argument("--model", "-m", default="gpt-3.5-turbo-0613", type=str, choices=MODELS)
    parser.add_argument("--num-responses", "-r", default=10, type=int)
    parser.add_argument("--max-tokens", "-t", default=1, type=int)
    parser.add_argument("--top-p", "-p", default=0.8, type=float)
    parser.add_argument("--filter-keyword", "-f", default="MISSING", type=str)
    parser.add_argument("--combine_responses", "-c", action="store_true")
    parser.add_argument("--timeout", default=10, type=int)
    parser.add_argument("--unescape-input", action="store_true")
    parser.add_argument("--escape-responses", action="store_true")
    parser.add_argument("--test", "-x", action="store_true")
    args = parser.parse_args()

    sys.stdin.reconfigure(encoding='utf-8')
    lines = (line for line in sys.stdin)
    header = next(lines).rstrip() # Get header of input data
    questions = util.get_questions(
        args.patterns, header,
        (l for l in lines),
        args.unescape_input,
        lambda query: args.filter_keyword not in query
    )

    if args.test:
        for q in questions:
            print(q[1])
    else:
        model = MODELS[args.model](args)
        model.run(
            questions=questions,
            header=header,
            num_responses=args.num_responses,
            max_tokens=args.max_tokens,
            combine_responses=args.combine_responses,
            escape=args.escape_responses
        )
