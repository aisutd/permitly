import argparse

def main():
    p = argparse.ArgumentParser(description='Permitly statute-only RAG demo')
    p.add_argument('command', choices=['ingest', 'ask'])
    p.add_argument('question', nargs='?')
    p.add_argument('--state', help='Filter by full state name, e.g. Texas')
    args = p.parse_args()
    if args.command == 'ask' and not args.question:
        p.error('ask requires a question in quotes')
    if __package__:
        from .core import ingest, ask
    else:
        from core import ingest, ask
    try:
        if args.command == 'ingest':
            ingest()
        else:
            print(ask(args.question, state=args.state))
    except RuntimeError as exc:
        p.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
