"""Vérifie que chaque jeu a exactement U users et U*P posts (comptage Datastore, REST)."""
from google.cloud import datastore
from google.cloud.datastore.query import PropertyFilter
c = datastore.Client(_use_grpc=False)
def cnt(q): return int(list(c.aggregation_query(q).count().fetch(timeout=300))[0][0].value)
def n_posts(px):
    q = c.query(kind='Post')
    q.add_filter(filter=PropertyFilter('author', '>=', f"{px}_u"))
    q.add_filter(filter=PropertyFilter('author', '<',  f"{px}_u\uffff"))
    return cnt(q)
def n_users(px):
    q = c.query(kind='User')
    q.add_filter(filter=PropertyFilter('__key__', '>=', c.key('User', f"{px}_u")))
    q.add_filter(filter=PropertyFilter('__key__', '<',  c.key('User', f"{px}_u\uffff")))
    return cnt(q)
jeux = [("base",1000,20),("u100",100,20),("u10000",10000,20),
        ("p10",100,10),("p100",100,100),("p1000",100,1000)] + \
       [(f"f{f:02d}",120,20) for f in range(5,101,5)]
for px,U,P in jeux:
    u, p = n_users(px), n_posts(px)
    print(f"{px:7s} users={u:6d}/{U:<6d} posts={p:7d}/{U*P:<7d} {'OK' if (u==U and p==U*P) else '<<< PROBLEME'}")
