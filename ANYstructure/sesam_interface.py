'''
Main file for handeling interface toward DNVGL software.
Consist mainly of helper functions.
'''

import ANYstructure.helper as hlp

def point_to_js_command(point_coord, point_name):
    '''
    Returning a js script.
    :param point_coord:
    :param point_name:
    :return:
    '''
    return point_name + ' = Point('+str(point_coord[0])+', 0, '+str(point_coord[2]) + ');'

def line_to_js_command_reference(from_point, to_point, curve_name):
    '''
    Returning a js script based on reference modelling.
    :param from_point:
    :param to_point:
    :param curve_name:
    :return:
    '''
    return curve_name +' = CreateLineTwoPoints(' + 'Point'+hlp.get_num(from_point)+'',  ''+ 'Point' + \
           hlp.get_num(to_point) + ');'

def section_property_to_js(kind, dimensions):
    '''
    Sct3 = BarSection(0.25, 0.015);
    Sct1 = UnsymISection(0.35, 0.02, 0, 0, 0, 0.15, 0.075, 0.02);
    Sct2 = LSection(0.3, 0.012, 0.1, 0.02);
    '''
    pass

class JSfile:
    '''
    An object representation of the js file.
    '''
    def __init__(self):
        super(JSfile, self).__init__()
        pass

if __name__ == '__main__':
    print('Hi')

