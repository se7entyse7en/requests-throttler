import argparse

import requests

from requests_throttler import BaseThrottler


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, default='http://www.google.com',
                        dest='url',
                        help='Specifies the url to which send the requests')
    parser.add_argument('--delay', type=float, default=3, dest='delay',
                        help='Specifies the delay to use')
    parser.add_argument('--num-reqs', type=int, default=5, dest='n_reqs',
                        help='Specifies the number of requests to send')
    args = parser.parse_args()
    return {'url': args.url, 'delay': args.delay, 'n_reqs': args.n_reqs}


def main():
    args = parse_args()
    bt = BaseThrottler(name='base-throttler', delay=args['delay'])
    reqs = []
    for i in range(0, args['n_reqs']):
        r = requests.Request(method='GET', url=args['url'], data='Request - ' + str(i + 1))
        reqs.append(r)

    with bt:
        throttled_requests = bt.multi_submit(reqs)

    for r in throttled_requests:
        print r.response

    print "Success: {s}, Failures: {f}".format(s=bt.successes, f=bt.failures)


if __name__ == '__main__':
    main()
