import requests


def main():
    bestseller_url = 'https://www.amazon.com/gp/bestsellers'
    res = requests.get(url=bestseller_url)
    # <Response [200]>
    print(res)


if __name__ == '__main__':
    main()