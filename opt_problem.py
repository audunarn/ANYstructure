import numpy as np

class MyProblem:
     def __init__(self, dim,upper_bounds,lower_bounds):
         super(MyProblem, self).__init__()
         self.dim = dim
         self.upper = upper_bounds
         self.lower = lower_bounds

     def fitness(self, x):
         return [sum(x*x)-sum(np.sqrt(x))]

     def get_bounds(self):
         return self.upper, self.lower

     def get_name(self):
         return "Sphere Function"

     def get_extra_info(self):
         return "\tDimensions: " + str(self.dim)


# prob = pg.problem(any_tester(10))
# algo = pg.algorithm(pg.pso(gen = 100, omega = 0.7298, eta1 = 2.05, eta2 = 2.05, max_vel = 0.5, variant = 5,
#                            neighb_type = 2, neighb_param = 4, memory = False))
# algo.set_verbosity(10)
# pop = pg.population(prob, 100)
# pop = algo.evolve(pop)
# print(pop.problem)
# uda = algo.extract(pg.pso)
# print(uda.get_log())
