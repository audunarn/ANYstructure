'''
Main file for handeling interface toward DNVGL software.
Consist mainly of helper functions.
'''

import ANYstructure.helper as hlp
import ANYstructure.pl_stf_window as plstf

def point_to_js_command(point_coord, point_name):
    '''
    Returning a js script.
    :param point_coord:
    :param point_name:
    :return:
    '''
    return point_name + ' = Point('+str(point_coord[0])+', 0, '+str(point_coord[1]) + ');\n'

def line_to_js_command_reference(from_point, to_point, curve_name):
    '''
    Returning a js script based on reference modelling.
    :param from_point:
    :param to_point:
    :param curve_name:
    :return:
    '''
    return curve_name +' = CreateLineTwoPoints(' + 'point'+str(from_point)+','+ ' point' + \
           str(to_point) + ');\n'

def section_property_to_js(section: plstf.Section = None):
    '''
    Sct3 = BarSection(0.25, 0.015);
    Sct1 = UnsymISection(0.35, 0.02, 0, 0, 0, 0.15, 0.075, 0.02);
    Sct2 = LSection(0.3, 0.012, 0.1, 0.02);
    '''

    if section.stf_type == 'T':
        js_def =  'UnsymISection('+str(section.stf_web_height)+', '+str(section.stf_web_thk)+', 0, 0, 0, '+ \
                  str(section.stf_flange_width)+', '+str(section.stf_flange_width/2)+', '+\
                  str(section.stf_flange_thk)+');\n'

    elif section.stf_type in ['L', 'L-bulb']:
        js_def =  'LSection('+str(section.stf_web_height)+', '+str(section.stf_web_thk)+', '+ \
                  str(section.stf_flange_width)+', '+ str(section.stf_flange_thk)+');\n'
    else:
        js_def =  'BarSection('+str(section.stf_web_height)+', '+str(section.stf_web_thk)+');\n'

    return section.__str__() +  ' = ' + js_def

class JSfile:
    '''
    An object representation of the js file.
    '''
    def __init__(self, points, lines, sections: plstf.Section = None, line_to_struc = None):
        super(JSfile, self).__init__()
        self._output_lines = list()
        self._points = points
        self._lines = lines
        self._sections = sections
        self._line_to_struc = line_to_struc

    @property
    def output_lines(self):
        return self._output_lines

    def write_points(self):
        ''' Writing point in the point list. '''
        for point_name, point_coord in self._points.items():
            self._output_lines.append(point_to_js_command(point_coord, point_name))

    def write_lines(self):
        ''' Writing the line list. '''
        for line_name, point_to_point in self._lines.items():
            self._output_lines.append(line_to_js_command_reference(point_to_point[0], point_to_point[1], line_name))

    def write_sections(self):
        ''' Exporting all sections. '''
        for section in self._sections:
            self._output_lines.append(section_property_to_js(section))

    def write_beams(self):
        '''
        Making beams and assining properties.
        Bm1 = Beam(line3);
        Bm1.section = T_400_0x12_0__250_0x14_0;
        '''
        for line_name, line_prop in self._line_to_struc.items():
            beam_name = 'ANYbm'+str(hlp.get_num(line_name))
            self.output_lines.append(beam_name+' = Beam('+line_name+');\n')
            section = plstf.Section(line_prop[0].get_structure_prop())
            self.output_lines.append(beam_name + '.section = '+section.__str__()+';\n')

if __name__ == '__main__':
    import ANYstructure.example_data as test
    from tkinter import filedialog

    imp_file = open('test_js.js', 'w')

    JS = JSfile(test.get_point_dict(), test.get_line_dict(), test.get_section_list(),
                line_to_struc=test.get_line_to_struc())
    JS.write_points()
    JS.write_lines()
    JS.write_sections()
    JS.write_beams()

    imp_file.writelines(JS.output_lines)
    imp_file.close()



