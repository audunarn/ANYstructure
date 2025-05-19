import numpy as np
import copy
# Not used in releases

from api import CylStru
import pandas as pd

def get_stresses(file = 'C:\DNV\RTHfisk\stress_results.txt'):
    if 'txt' in file:
        nas = ['',]
        spaces = ''
        for val in range(20):
            spaces += ' '
            nas.append(spaces)
        nas_final = list()
        for val in nas:
            nas_final.append(val + 'N/A')

        pd_data = pd.read_csv(file,header=0, sep=r'\t', engine='python',
                              na_values = nas_final)
        pd_data.columns = [val.strip() for val in pd_data.columns.values]
        pd.set_option('display.max_columns', None)
        print(pd_data)
    else:
        pd_data = pd.read_excel(file)
    # for val in pd_data.iterrows():
    #     print(val[1])
    #     quit()
    return pd_data

def calc_buckling_single(val):

    my_cyl = CylStru(calculation_domain='Longitudinal Stiffened panel')
    my_cyl.set_stresses(smsd=val[1].SIGMX / 1e6, tQsd=abs(val[1].TAUMXY) / 1e6, shsd=val[1].SIGMY / 1e6)
    my_cyl.set_material(mat_yield=355, emodule=210000, material_factor=1.1, poisson=0.3)
    my_cyl.set_imperfection()
    my_cyl.set_fabrication_method()
    my_cyl.set_end_cap_pressure_included_in_stress(is_included=True)
    my_cyl.set_uls_or_als(kind='ULS')
    # my_cyl.set_exclude_ring_stiffener()
    my_cyl.set_length_between_girder(val=3300)
    my_cyl.set_panel_spacing(val=680)
    my_cyl.set_shell_geometry(radius=13000 / 2, thickness=1000 * val[1].Thickness, tot_length_of_shell=30000,
                              distance_between_rings=3300)
    my_cyl.set_longitudinal_stiffener(hw=260, tw=12, bf=49, tf=28, spacing=680)
    # my_cyl.set_ring_girder(hw=500, tw=15, bf=200, tf=25, stf_type='T', spacing=700)
    my_cyl.set_shell_buckling_parmeters()
    results = my_cyl.get_buckling_results()
    scan_idx = tuple(val[1].ScanIndex.split(','))[1].replace(' ','')
    return [scan_idx, val[1]['X-coord'], val[1]['Y-coord'], val[1]['Z-coord'],
            val[1].Thickness, val[1].SIGMX, val[1].SIGMY, val[1].TAUMXY, val[1].Element,
            results['Unstiffened shell'], results['Longitudinal stiffened shell'], results['Ring stiffened shell'],
            max([val for val in [results['Unstiffened shell'], results['Longitudinal stiffened shell'],
                                 results['Ring stiffened shell']] if val is not None])]

def calc_buckling(stresses):
    res_list = list()
    for val in stresses.iterrows():

        my_cyl = CylStru(calculation_domain='Longitudinal Stiffened shell')
        my_cyl.set_stresses(sasd=val[1].SIGMX/1e6, tQsd=abs(val[1].TAUMXY)/1e6, shsd=val[1].SIGMY/1e6)
        my_cyl.set_material(mat_yield=355, emodule=210000, material_factor=1.1, poisson=0.3)
        my_cyl.set_imperfection()
        my_cyl.set_fabrication_method()
        my_cyl.set_end_cap_pressure_included_in_stress(is_included=True)
        my_cyl.set_uls_or_als(kind='ULS')
        #my_cyl.set_exclude_ring_stiffener()
        #my_cyl.set_length_between_girder(val=8000)
        my_cyl.set_panel_spacing(val=680)
        my_cyl.set_shell_geometry(radius=13000/2,thickness=1000*val[1].Thickness, tot_length_of_shell=30000,
                                  distance_between_rings=3300)
        my_cyl.set_longitudinal_stiffener(hw=260, tw=23, bf=49, tf=28, spacing=680)
        #my_cyl.set_ring_girder(hw=500, tw=15, bf=200, tf=25, stf_type='T', spacing=700)
        my_cyl.set_shell_buckling_parmeters()
        results = my_cyl.get_buckling_results()
        res_list.append((val[1].Case, val[1]['X-coord'], val[1]['Y-coord'], val[1]['Z-coord'],
                         val[1].Thickness, val[1].SIGMX, val[1].SIGMY, val[1].TAUMXY, val[1].Element,
                         results['Unstiffened shell']))

    final_pd = pd.DataFrame(res_list, columns=['Load case', 'x', 'y', 'z', 'Thickness', 'SIGMX', 'SIGMY', 'TAUMXY',
                                               'Element', 'UF'])
    final_pd.to_csv(r'C:\DNV\RTHfisk\buckling_res.csv')

def read_generated_csv(file = r'C:\DNV\RTHfisk\|.csv'):
    data = pd.read_csv(file, index_col=0)
    return data

def calc_cyl_buckling_from_folder(folder, files, add_to_file_name: str = ''):
    reslist = list()
    reslist_puls = list()
    for file in files:
        stress_file = get_stresses(folder + file)
        for stress in stress_file.iterrows():
            if not np.isnan(stress[1].Thickness):
                this_result = calc_buckling_single(stress)
                element = this_result[8]
                this_result.insert(0, file)
                this_result.insert(0, str(element)+ '_' + file)
                reslist.append(tuple(this_result))

    all_res = pd.DataFrame(reslist, columns=['id', 'File', 'ScanIndex', 'x', 'y', 'z', 'thk', 'SIGMX', 'SIGMY',
                                             'TAUMXY', 'Element', 'Unstiffened shell', 'Longitudinal stiffened shell',
                                             'Ring stiffened shell', 'Max UF'])
    all_res['PULS SIGMX'] = -1*all_res['SIGMX'].values/1e6
    all_res['PULS SIGMY1'] = -1 * all_res['SIGMY'].values / 1e6
    all_res['PULS SIGMY2'] = -1 * all_res['SIGMY'].values / 1e6
    all_res['PULS TAUMXY'] = -1 * all_res['TAUMXY'].values / 1e6
    all_res['PULS THICKNESS'] = all_res['thk'].values * 1000
    all_res.to_excel(folder + 'buckling_results' + add_to_file_name+'.xlsx')


if __name__ == '__main__':
    #stresses = read_generated_csv()
    # stresses = get_stresses()
    # buckling = calc_buckling(stresses=stresses)

    folder = 'C:\DNV\Workspaces\\OV15MW_Disc25m\\OV_Octa_Gen2_SaAr_NoCo_D1\\Analysis_max_min_1\\'
    files = ['Dstress_TAUXY_absmax', 'Dstress_SIGMY_max', 'Dstress_SIGMY_min', 'Dstress_SIGMX_max', 'Dstress_SIGMX_min']
    files = [file + '.txt' for file in files]
    calc_cyl_buckling_from_folder(folder, files, add_to_file_name='_1')