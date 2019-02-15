def main():
    with open("/etc/fstab", "r") as f:
        print(f.read())

if __name__ == "__main__":
    main()
