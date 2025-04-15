from . import server


def main():
    return server.main()


# Optionally expose other important items at package level
__all__ = ["main", "server"]
