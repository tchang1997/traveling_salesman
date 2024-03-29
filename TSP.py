import numpy as np # array operations
import random # stochastic route generation
import operator # for fancy dictionary sort
from collections import OrderedDict, deque # sorted from dict->dict; keep track of number of times we try to escape from local minima
import argparse 
import sys
import matplotlib.pyplot as plt # yes

class City:
    def __init__(self, n, x, y):
        self.n = int(n)
        self.x = int(x)
        self.y = int(y)

    def distance_from(self, other):
        return np.sqrt(abs(self.x - other.x) ** 2 + abs(self.y - other.y) ** 2)

    def __repr__(self):
        return "City {}: ({}, {})".format(self.n, self.x, self.y)

def inv_l2(route):
    l2 = 0
    for loc_a, loc_b in zip(route[:-1], route[1:]):
        l2 += loc_a.distance_from(loc_b)
    return 1 / l2

class TSPProblem:
    def __init__(self, city_file):
        self.cities = []
        with open(city_file) as f:
            for line in f:
                if line[0] is not '#':
                    city_num, city_x, city_y = line.split()
                    self.cities.append(City(city_num, city_x, city_y))

    def createRoute(self):
        return random.sample(self.cities, len(self.cities))

    def createPopulation(self, pop_size):
        return [self.createRoute() for _ in range(pop_size)]
    
    def rankRoutes(self, population, fitness_func=inv_l2):
        fitness_results = {i: fitness_func(route) for i, route in enumerate(population)}
        sorted_fitness = OrderedDict(sorted(fitness_results.items(), key=operator.itemgetter(1), reverse=True))
        return sorted_fitness

    def chooseParents(self, routes, fitness_dict, n_elites): 
        result = []
        for i in range(n_elites):
            result.append(np.array(routes[list(fitness_dict.keys())[i]]))
        result += self.resample([routes[idx] for idx in fitness_dict.keys()], fitness_dict.values(), len(fitness_dict) - n_elites)  
        return result


    def resample(self, routes, rankings, sample_size): 
        return list(np.array(routes)[np.random.choice(len(routes), size=sample_size, p=[w / sum(rankings) for w in rankings]), :])

    def breed(self, parent1, parent2):
        loc1, loc2 = random.sample(range(len(parent1)), 2) 
        gene = parent1[loc1 : loc2]  
        child = [None] * len(parent1) # sentinel value
        for i in range(loc1, loc2, 1):
            child[i] = gene[i - loc1]
        parent2_iter = 0
        for i in range(len(child)):
            if child[i] is None:
                next_trait = parent2[parent2_iter]
                while next_trait in gene:
                    parent2_iter += 1 
                    next_trait = parent2[parent2_iter]
                child[i] = parent2[parent2_iter]
                parent2_iter += 1
        assert(len(child) == len(set(child)))
        return child

    def crossover(self, routes, n_elite):
        next_gen = routes[:n_elite]
        n_children = len(routes) - n_elite 
        for _ in range(n_children):
            parent1, parent2 = random.sample(routes, 2)
            next_gen.append(self.breed(parent1, parent2))
        return next_gen

    def mutate(self, routes, p):
        if random.random() < p:
            src, dest = random.sample(range(len(routes)), 2)
            temp = routes[dest]
            routes[dest] = routes[src]
            routes[src] = temp
        return routes

    def iterate(self, curr_gen, n_elite=10, mut_rate=0.001):
        ranked = self.rankRoutes(curr_gen) # rank the current generation
        parents = self.chooseParents(curr_gen, ranked, n_elite)
        crossed = self.crossover(parents, n_elite)
        mutated = self.mutate(crossed, mut_rate)
        return mutated

    def run(self, n_iters=1000, n_elite=10, mut_rate=0.001, pop_size=100, escape_attempts=10, report_every=100):
        pop = self.createPopulation(pop_size)
        last_max_deque = deque() 
        for i in range(n_iters):
            pop = self.iterate(pop, n_elite, mut_rate)
            if i % report_every == 0:
                print("=====Result after", i+1, "iteration(s)=====")
                self.report(pop)
            if len(last_max_deque) == escape_attempts:
                if len(set(last_max_deque)) <= 1: break
                last_max_deque.popleft()
            last_max_deque.append(list(self.rankRoutes(pop).keys())[0])
        fitness, best_route = self.report(pop)
        self.plot(fitness, best_route)

    def report(self, population, fitness_func=inv_l2):
        rankings = self.rankRoutes(population)
        best_route = population[list(rankings.keys())[0]]
        print("Length:", 1 / fitness_func(best_route))
        print("Route:", str(list(best_route)))
        return 1 / fitness_func(best_route), list(best_route)

    def plot(self, fitness, route):
        x = [city.x for city in route]
        y = [city.y for city in route]
        plt.title('Traveling Salesman Solution')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.scatter(x, y)
        plt.plot(x, y, '-o')
        plt.text(0, max(y), "Length: "  + str(fitness), horizontalalignment='left', verticalalignment='center')
        plt.show()
            

if __name__ == '__main__':
    psr = argparse.ArgumentParser()
    psr.add_argument('--file', type=str, default='maps/small_city', help='file with cities and coordinates')
    psr.add_argument('--iterations', type=int, default=1000, help='number of iterations before termination (if no convergence)')
    psr.add_argument('--num-elite', type=int, default=10, help='number of "elite" genes that are selected for reproduction')
    psr.add_argument('--generation', type=int, default=100, help='generation size')
    psr.add_argument('--mutation-rate', type=float, default=0.001, help='mutation rate; probability of a swap mutation in a single generation')
    psr.add_argument('--escape_attempts', type=int, default=10, help='epsilon; convergence parameter')
    psr.add_argument('--report', type=int, default=100, help='reporting frequency')
    args = psr.parse_args()
    if type(args.iterations) is not int:
        print("ERROR: Number of iterations must be an integer.")
        sys.exit(0)
    if type(args.num_elite) is not int:
        print("ERROR: Number of elite genes must be an integer.")
        sys.exit(0)
    if type(args.generation) is not int:
        print("ERROR: Generation size must be an integer.")
        sys.exit(0)
    if args.generation < args.num_elite:
        print("ERROR: Generation size must be larger than the number of elite genes retained.")
        sys.exit(0)
    if type(args.report) is not int:
        print("ERROR: Reporting frequency must be an integer.")
        sys.exit(0)
    if args.mutation_rate < 0 or args.mutation_rate > 1:
        print("ERROR: Mutation rate must be a probability between 0 and 1, inclusive")
        sys.exit(0)
    if type(args.escape_attempts) is not int:
        print("ERROR: Number of escape attempts from local minima must be an integer.")
    tsp = TSPProblem(args.file)
    tsp.run(n_iters=args.iterations, n_elite=args.num_elite, mut_rate=args.mutation_rate, pop_size=args.generation, escape_attempts=args.escape_attempts, report_every=args.report)



