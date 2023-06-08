from aiknows import ai

# def test_follow_up():
#     r, sess = ai('sum numbers in x', x=[1, 2, 3, 4, 5], save_session=True)
#     assert r == 15
#     assert sess.ai('multiply numbers in x') == 120


# def test_dataframe(cities_df):
#     # someties it's ok, most of the times fail
#     r = ai('return the two most distant cities names in df\ndon\'t use geopy', df=cities_df)
#     assert set(r) == {'West Palm Beach', 'Vancouver'}
