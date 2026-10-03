"""
Updates dark_mode.svg and light_mode.svg with live GitHub stats.

Required environment variables:
  ACCESS_TOKEN  GitHub personal access token (see README for scopes)
  USER_NAME     your GitHub username

Adapted from the structure of Andrew6rant/Andrew6rant.
"""
import hashlib
import json
import os
import sys
import time

import requests
from lxml import etree

TOKEN = os.environ['ACCESS_TOKEN']
USER_NAME = os.environ['USER_NAME']
HEADERS = {'Authorization': 'bearer ' + TOKEN}
API = 'https://api.github.com/graphql'
CACHE_FILE = 'cache/' + hashlib.sha256(USER_NAME.encode()).hexdigest() + '.json'
ALL_AFFILIATIONS = ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER']
# sha256('owner/name') of repos whose lines are not counted (their commits still are).
# Hashes, not names, because this file is public and the repos are private.
LOC_EXCLUDE = {
    '6700f163fb9723d72a25de7e83f7e004d9bbf81f653cdb4f96008f3b86bd2be7',
    'e8499d956630957fe883a529c796b38c2788f46ea141d2229e7ea5cd4bda2c8e',
}
CALLS = 0


def gql(query, variables):
    """Send one GraphQL request. Raise with the response body on failure."""
    global CALLS
    CALLS += 1
    r = requests.post(API, json={'query': query, 'variables': variables}, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f'GraphQL failed with {r.status_code}: {r.text}')
    body = r.json()
    if 'errors' in body:
        raise RuntimeError(f'GraphQL errors: {body["errors"]}')
    return body['data']


def user_info():
    data = gql('query($l:String!){user(login:$l){id createdAt followers{totalCount}}}', {'l': USER_NAME})
    u = data['user']
    return u['id'], u['createdAt'], u['followers']['totalCount']


def list_repos(affiliations):
    """Return every repo as {name, stars, commits}. Pages 50 at a time to avoid 502 errors."""
    query = '''
    query($aff:[RepositoryAffiliation],$l:String!,$c:String){
      user(login:$l){
        repositories(first:50, after:$c, ownerAffiliations:$aff){
          pageInfo{endCursor hasNextPage}
          nodes{
            nameWithOwner
            stargazerCount
            defaultBranchRef{target{... on Commit{history{totalCount}}}}
          }
        }
      }
    }'''
    repos, cursor = [], None
    while True:
        page = gql(query, {'aff': affiliations, 'l': USER_NAME, 'c': cursor})['user']['repositories']
        for n in page['nodes']:
            ref = n['defaultBranchRef']
            total = ref['target']['history']['totalCount'] if ref else 0
            repos.append({'name': n['nameWithOwner'], 'stars': n['stargazerCount'], 'commits': total})
        if not page['pageInfo']['hasNextPage']:
            return repos
        cursor = page['pageInfo']['endCursor']


def count_repo_loc(owner, name, owner_id):
    """Walk a repo's commit history and sum additions, deletions and commits authored by you."""
    query = '''
    query($n:String!,$o:String!,$c:String){
      repository(name:$n, owner:$o){
        defaultBranchRef{target{... on Commit{history(first:100, after:$c){
          pageInfo{endCursor hasNextPage}
          nodes{additions deletions author{user{id}}}
        }}}}
      }
    }'''
    adds = dels = mine = 0
    cursor = None
    while True:
        ref = gql(query, {'n': name, 'o': owner, 'c': cursor})['repository']['defaultBranchRef']
        if ref is None:
            return 0, 0, 0
        hist = ref['target']['history']
        for c in hist['nodes']:
            user = c['author']['user']
            if user and user['id'] == owner_id:
                mine += 1
                adds += c['additions']
                dels += c['deletions']
        if not hist['pageInfo']['hasNextPage']:
            return adds, dels, mine
        cursor = hist['pageInfo']['endCursor']


def load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs('cache', exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=1, sort_keys=True)


def loc_totals(repos, owner_id):
    """
    Only re-walk a repo when its total commit count changed since the last run.
    The cache is saved after every repo so a crash or rate limit keeps progress.
    """
    cache = load_cache()
    live = {hashlib.sha256(r['name'].encode()).hexdigest(): r for r in repos}
    cache = {k: v for k, v in cache.items() if k in live}  # drop repos that no longer exist
    for key, repo in live.items():
        entry = cache.get(key)
        if entry and entry['total_commits'] == repo['commits']:
            continue
        owner, name = repo['name'].split('/')
        try:
            adds, dels, mine = count_repo_loc(owner, name, owner_id)
        except Exception:
            save_cache(cache)
            raise
        cache[key] = {'total_commits': repo['commits'], 'my_commits': mine, 'adds': adds, 'dels': dels}
        save_cache(cache)
    save_cache(cache)
    adds = sum(v['adds'] for k, v in cache.items() if k not in LOC_EXCLUDE)
    dels = sum(v['dels'] for k, v in cache.items() if k not in LOC_EXCLUDE)
    mine = sum(v['my_commits'] for v in cache.values())
    return adds, dels, mine


def fmt(n):
    return f'{n:,}'


def set_text(root, element_id, text):
    el = root.find(f".//*[@id='{element_id}']")
    if el is not None:
        el.text = text


def write_svg(path, stats):
    tree = etree.parse(path)
    root = tree.getroot()
    set_text(root, 'repo_data', fmt(stats['repos']))
    set_text(root, 'commit_data', fmt(stats['commits']))
    set_text(root, 'loc_data', fmt(stats['loc_net']))
    set_text(root, 'loc_add', fmt(stats['loc_add']))
    set_text(root, 'loc_del', fmt(stats['loc_del']))
    tree.write(path, encoding='utf-8', xml_declaration=True)


def main():
    t0 = time.perf_counter()
    owner_id, _created, followers = user_info()
    owned = list_repos(['OWNER'])
    everything = list_repos(ALL_AFFILIATIONS)
    adds, dels, commits = loc_totals(everything, owner_id)

    stats = {
        'repos': len(owned),
        'contrib': len(everything),
        'stars': sum(r['stars'] for r in owned),
        'commits': commits,
        'followers': followers,
        'loc_add': adds,
        'loc_del': dels,
        'loc_net': adds - dels,
    }
    for svg in ('dark_mode.svg', 'light_mode.svg'):
        write_svg(svg, stats)

    print(f'Done in {time.perf_counter() - t0:.1f}s with {CALLS} GraphQL calls')
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    sys.exit(main())
