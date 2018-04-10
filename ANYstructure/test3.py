from matplotlib import pyplot as plt
import json
import numpy as np

with open('C:\\GridOnly.txt', 'r') as file:
    grid_dict = json.load(file)
    grid = grid_dict['grid']

def discrete_matshow(data):
    fig = plt.figure(figsize=[12,8])
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.0)
    # get discrete colormap
    cmap = plt.get_cmap('Accent_r', np.max(data) - np.min(data) + 1)
    # set limits .5 outside true range
    cax = ax.matshow(data, cmap=cmap, vmin=np.min(data) - .5, vmax=np.max(data) + .5)
    # tell the colorbar to tick at integers
    colb = fig.colorbar(cax, ticks=np.arange(np.min(data), np.max(data) + 1), shrink = 0.8)
    colb.set_ticks([-1,0,1]+[num+2 for num in range(comps)])
    colb.set_ticklabels(['BHD/Deck','Not used', 'External']+['Comp'+str(num+2) for num in range(comps)])

comps = 3

# generate data
discrete_matshow(grid)
plt.suptitle('Compartments returned from search operation displayed below', fontsize = 15)

plt.xscale('linear')
plt.axis('off')
plt.show()