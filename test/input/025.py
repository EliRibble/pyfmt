"This is the docstring for a module"
import datetime
import logging

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("It is now %s", datetime.datetime.utcnow().isoformat())

if __name__ == "__main__":
    main()
