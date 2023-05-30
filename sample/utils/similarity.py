
from fuzzywuzzy import fuzz
import textdistance


match, kw = "U想家", "U想家APPV1.0"

ratio1 = textdistance.cosine.similarity(match, kw)
ratio2 = textdistance.jaro_winkler(match, kw)

# print("===========Edit based===========")
# ratio = textdistance.jaro_winkler(match, kw)
# print("jaro_winkler", ratio, match, kw)  # 开头开始匹配
# print("===========Token based===========")
# ratio = textdistance.cosine.similarity(match, kw)
# print("cosine", ratio, match, kw)
# ratio = textdistance.jaccard(list(match), list(kw))  # A∩B / A∪B
# print("jaccard", ratio, match, kw)
# ratio = textdistance.sorensen(list(match), list(kw))  # 2|A∩B| / |A|+|B|
# print("sorensen", ratio, match, kw)
# print("===========Sequence based===========")
# ratio = textdistance.ratcliff_obershelp(match, kw)
# print("ratcliff_obershelp", ratio, match, kw)
# ratio = fuzz.token_sort_ratio(match, kw) / float(100)  # 0-100，100表示完全相同
# ratio = fuzz.partial_ratio(match, kw) / float(100)  # 部分匹配