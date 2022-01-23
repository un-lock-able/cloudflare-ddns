from ddns import DDNS
import sys

if __name__ == "__main__":
    try:
        DDNS.main(sys.argv[1])
    except IndexError:
        DDNS.main()
