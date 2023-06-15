
m time import sleep
from random import randint


def main():
    # sleeps a random time between 1-50ms
    amount = randint(1, 50)
    print(f"sleeping for {amount}ms")
    sleep(amount / 1000)

    return amount

if __name__ == "__main__":
    main()

