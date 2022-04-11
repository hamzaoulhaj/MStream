import numpy as np

def preprocess(x,i):
    categ = []
    numeric = []
    for col in drop_columns:
        x.pop(col)
    for col in categ_columns:
        categ.append(int(x.pop(col)))
    label = x.pop('normal.')
    for key, value in x.items():
        numeric.append(float(value))
    return({'numeric' : numeric, 'categ' : categ, 'time' : i},label)

class Numerichash:

    def __init__(self,r,b):
        self.num_rows = r
        self.num_buckets = b
        self.count = np.zeros((r,b))

    def hash(self, cur_node):
        cur_node = cur_node * (self.num_buckets - 1)
        bucket = int(cur_node)
        if (bucket > 0):
            bucket = (bucket % self.num_buckets + self.num_buckets) % self.num_buckets
        return bucket

    def insert(self, cur_node, weight):
        bucket = self.hash(cur_node)
        self.count[0][bucket] += weight

    def get_count(self, cur_node):
        bucket = self.hash(cur_node)
        return self.count[0][bucket]

    def clear(self):
        self.count = np.zeros(self.num_rows,self.num_buckets)

    def lower(self,factor):
        for  i in range(self.num_rows):
            for j in range(self.num_buckets):
                self.count[i][j] = self.count[i][j] * factor

class Categhash:

    def __init__(self, r, b):
        self.num_rows = r
        self.num_buckets = b
        self.count = np.zeros((self.num_rows,self.num_buckets))
        self.hash_a = np.zeros(self.num_rows)
        self.hash_b = np.zeros(self.num_rows)
        for i in range(self.num_rows): #a is in [1, p-1]; b is in [0, p-1]
            self.hash_a[i] = np.random.randint(self.num_buckets - 1) + 1
            self.hash_b[i] = np.random.randint(self.num_buckets)
        
    def hash(self, a , i):
        resid = (a * self.hash_a[i] + self.hash_b[i]) % self.num_buckets
        return int(resid) + (resid < 0) * self.num_buckets

    def insert(self, cur_int, weight):
        for i in range(self.num_rows):
            bucket = self.hash(cur_int, i)
            self.count[i][bucket] += weight

    def get_count(self, cur_int):
        bucket = self.hash(cur_int, 0)
        min_count = self.count[0][bucket]
        for i in range(self.num_rows):
            bucket = self.hash(cur_int, i)
            min_count = min(min_count, self.count[i][bucket])
        return min_count

    def clear(self):
        self.count = np.zeros((self.num_rows,self.num_buckets))

    def lower(self, factor):
        for i in range(self.num_rows):
            for j in range(self.num_buckets):
              self.count[i][j] = self.count[i][j] * factor


class Recordhash:

    def __init__(self, r, b, dim1, dim2):
        self.num_rows = r
        self.num_buckets = b
        self.dimension1 = dim1
        self.dimension2 = dim2
        self.count = np.zeros((self.num_rows,self.num_buckets))

        self.num_recordhash = []
        for i in range(self.num_rows):
            log_bucket = int(np.log2(self.num_buckets)) + 1
            self.num_recordhash.append(np.random.randn(log_bucket,self.dimension1))

        self.cat_recordhash = []
        for i in range(self.num_rows):
            vect = []
            for k in range(self.dimension2 - 1):
                vect.append(np.random.randint(self.num_buckets - 1)+ 1)
            if self.dimension2 > 0:
                vect.append(np.random.randint(self.num_buckets))
            self.cat_recordhash.append(vect)


    def numerichash(self, cur_numeric, i):
        bitcounter = 0
        log_bucket = int(np.log2(self.num_buckets)) + 1
        b = ''
        for iter in range(log_bucket):
            sum = 0
            for k in range(self.dimension1):
                sum += self.num_recordhash[i][iter][k] * cur_numeric[k]
            b = str(int(sum>=0)) + b
        return int('0b'+ b, base = 2)


    def categhash(self, cur_categ, i):
        counter = 0
        resid = 0
        for k in range(self.dimension2):
            resid += (self.cat_recordhash[i][counter] * cur_categ[counter]) % self.num_buckets
            counter += 1
        return resid + (resid < 0) * self.num_buckets


    def insert(self, cur_numeric, cur_categ,weight):
        for i in range(self.num_rows):
            bucket1 = self.numerichash(cur_numeric, i)
            bucket2 = self.categhash(cur_categ, i)
            bucket = (bucket1 + bucket2) % self.num_buckets
            self.count[i][bucket] += weight


    def get_count(self, cur_numeric, cur_categ):
        bucket1 = self.numerichash(cur_numeric, 0)
        bucket2 = self.categhash(cur_categ, 0)
        bucket = (bucket1 + bucket2) % self.num_buckets
        min_count = self.count[0][bucket]

        for i in range(self.num_rows):
            bucket1 = self.numerichash(cur_numeric, i)
            bucket2 = self.categhash(cur_categ, i)
            bucket = (bucket1 + bucket2) % self.num_buckets
            min_count = min(min_count, self.count[i][bucket])
        return min_count


    def clear(self): 
        self.count = np.zeros(self.num_rows,self.num_buckets)


    def lower(self,factor):
        for  i in range(self.num_rows):
            for j in range(self.num_buckets):
                self.count[i][j] = self.count[i][j] * factor

def counts_to_anom(tot, cur, cur_t):
    cur_mean = tot / cur_t
    sqerr = max(0, cur - cur_mean)**2
    return sqerr / cur_mean + sqerr / (cur_mean * max(1, cur_t - 1))

class MStream():
    
    def __init__(self, num_rows, num_buckets, factor, dimension1, dimension2):
        self.num_rows = num_rows
        self.num_buckets = num_buckets
        self.factor = factor
        self.dimension1 = dimension1
        self.dimension2 = dimension2
        self.cur_t = 1

        self.cur_count = Recordhash(num_rows, num_buckets, dimension1, dimension2)
        self.total_count = Recordhash(num_rows, num_buckets, dimension1, dimension2)

        self.numeric_score = [Numerichash(num_rows, num_buckets) for i in range(dimension1)]
        self.numeric_total = [Numerichash(num_rows, num_buckets) for i in range(dimension1)]
        self.categ_score = [Categhash(num_rows, num_buckets) for i in range(dimension2)]
        self.categ_total = [Categhash(num_rows, num_buckets) for i in range(dimension2)]

        if dimension1 > 0 : 
            self.max_numeric = [-float('inf') for i in range(dimension1)]
            self.min_numeric = [float('inf') for i in range(dimension1)]


    def learn_one(self, x):
        
        if (x['time'] > self.cur_t):
            self.cur_count.lower(self.factor)
            for j in range(self.dimension1):
                self.numeric_score[j].lower(self.factor)
            for j in range(self.dimension2):
                self.categ_score[j].lower(self.factor)
            self.cur_t = x['time']

        cur_numeric = x['numeric']
        cur_categ = x['categ']

        for node_iter in range(self.dimension1):
            cur_numeric[node_iter] = np.log10(1 + cur_numeric[node_iter])
            self.min_numeric[node_iter] = min(self.min_numeric[node_iter], cur_numeric[node_iter])
            self.max_numeric[node_iter] = max(self.max_numeric[node_iter], cur_numeric[node_iter])

            if (self.max_numeric[node_iter] == self.min_numeric[node_iter]):
                cur_numeric[node_iter] = 0
            else:
                cur_numeric[node_iter] = (cur_numeric[node_iter] - self.min_numeric[node_iter])/(self.max_numeric[node_iter] - self.min_numeric[node_iter])
            self.numeric_score[node_iter].insert(cur_numeric[node_iter], 1)
            self.numeric_total[node_iter].insert(cur_numeric[node_iter], 1)

        self.cur_count.insert(cur_numeric, cur_categ, 1)
        self.total_count.insert(cur_numeric, cur_categ, 1)

        for node_iter in range(self.dimension2):
            self.categ_score[node_iter].insert(cur_categ[node_iter], 1)
            self.categ_total[node_iter].insert(cur_categ[node_iter], 1)

        return(self)

    def score_one(self, x):
        if (x['time'] > self.cur_t):
            self.cur_count.lower(self.factor)
            for j in range(self.dimension1):
                self.numeric_score[j].lower(self.factor)
            for j in range(self.dimension2):
                self.categ_score[j].lower(self.factor)
            self.cur_t = x['time']

        cur_numeric = x['numeric']
        cur_categ = x['categ']
        sum = 0.0
        for node_iter in range(self.dimension1):
            cur_numeric[node_iter] = np.log10(1 + cur_numeric[node_iter])
            self.min_numeric[node_iter] = min(self.min_numeric[node_iter], cur_numeric[node_iter])
            self.max_numeric[node_iter] = max(self.max_numeric[node_iter], cur_numeric[node_iter])
            if (self.max_numeric[node_iter] == self.min_numeric[node_iter]):
                cur_numeric[node_iter] = 0
            else:
                cur_numeric[node_iter] = (cur_numeric[node_iter] - self.min_numeric[node_iter])/(self.max_numeric[node_iter] - self.min_numeric[node_iter])
            self.numeric_score[node_iter].insert(cur_numeric[node_iter], 1)
            self.numeric_total[node_iter].insert(cur_numeric[node_iter], 1)
            t = counts_to_anom(self.numeric_total[node_iter].get_count(cur_numeric[node_iter]),
                               self.numeric_score[node_iter].get_count(cur_numeric[node_iter]), 
                               self.cur_t)
            sum += t

        self.cur_count.insert(cur_numeric, cur_categ, 1)
        self.total_count.insert(cur_numeric, cur_categ, 1)

        for node_iter in range(self.dimension2):
            self.categ_score[node_iter].insert(cur_categ[node_iter], 1)
            self.categ_total[node_iter].insert(cur_categ[node_iter], 1)
            t = counts_to_anom(self.categ_total[node_iter].get_count(cur_categ[node_iter]),
                               self.categ_score[node_iter].get_count(cur_categ[node_iter]), 
                               self.cur_t)
            sum += t

        cur_score = counts_to_anom(self.total_count.get_count(cur_numeric, cur_categ),
                                   self.cur_count.get_count(cur_numeric, cur_categ), 
                                   self.cur_t)
        sum += cur_score
        score = np.log(1 + sum)

        return score