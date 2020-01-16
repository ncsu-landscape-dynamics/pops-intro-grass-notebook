#!usr/bin/env python3

import os
import sys
import subprocess
import folium
import json


def initialize_GRASS_notebook(binary, grassdata, location, mapset):

    # create GRASS GIS runtime environment
    gisbase = subprocess.check_output([binary, "--config", "path"], universal_newlines=True).strip()
    os.environ['GISBASE'] = gisbase
    sys.path.append(os.path.join(gisbase, "etc", "python"))

    # do GRASS GIS imports
    import grass.script as gs
    import grass.script.setup as gsetup

    # set GRASS GIS session data
    rcfile = gsetup.init(gisbase, grassdata, location, mapset)
    # default font displays
    os.environ['GRASS_FONT'] = 'sans'
    # overwrite existing maps
    os.environ['GRASS_OVERWRITE'] = '1'
    gs.set_raise_on_error(True)
    gs.set_capture_stderr(True)
    # set display modules to render into a file (named map.png by default)
    os.environ['GRASS_RENDER_IMMEDIATE'] = 'cairo'
    os.environ['GRASS_RENDER_FILE_READ'] = 'TRUE'
    os.environ['GRASS_LEGEND_FILE'] = 'legend.txt'


def show(raster):
    from IPython.display import Image
    import grass.script as gs
    region = gs.region()
    gs.run_command('d.erase')
    gs.use_temp_region()
    gs.run_command('g.region', align='ortho', n=region['n'], s=region['s'], e=region['e'], w=region['w'])
    gs.run_command('d.rast', map='ortho')
    gs.run_command('d.rast', map=raster, values=0, flags='i')
    gs.run_command('d.vect', map='NHDFlowline', where="FCODE >= 46006", color='30:144:255')
    gs.run_command('d.vect', map='roads', where="FULLNAME is not NULL", color='165:159:159', width=2)
    gs.run_command('d.barscale', at=[38.0,97.0], flags='n', style='both_ticks', segment=5, color='255:255:255', bgcolor='none')
    gs.del_temp_region()
    return Image("map.png")


def show_interactively(raster, opacity=0.8):
    import grass.script as gs
    info = gs.raster_info(raster)
    raster = raster.split('@')[0]
    gs.mapcalc('{r}_processed = if({r} == 0, null(), int({r}))'.format(r=raster))
    gs.run_command('r.colors', map=raster + '_processed', raster=raster)
    gs.run_command('r.out.gdal', input=raster + '_processed', output=raster + '_spm.tif', type='Byte')
    gs.run_command('g.remove', type='raster', name=raster + '_processed', flags='f')
    subprocess.call(['gdalwarp', '-t_srs', 'EPSG:3857',  raster + '_spm.tif', raster + '_merc.tif', '-overwrite'])
    subprocess.call(['gdal_translate', '-of', 'png', raster + '_merc.tif', raster + '_merc.png'])
    info = subprocess.check_output(['gdalinfo', '-json', '-noct', '-nomd', raster + '_merc.png'], universal_newlines=True)
    coors = json.loads(info)['wgs84Extent']['coordinates'][0]
    lon = [pt[0] for pt in coors]
    lat = [pt[1] for pt in coors]
    minlat = min(lat)
    minlon = min(lon)
    maxlat = max(lat)
    maxlon = max(lon)
    m = folium.Map(location=[(maxlat + minlat) / 2, (maxlon + minlon) / 2])
    img = folium.raster_layers.ImageOverlay(
            name=raster,
            image=raster + '_merc.png',
            bounds=[[minlat, minlon], [maxlat, maxlon]],
            opacity=opacity,
            interactive=True,
            cross_origin=False,
        )
    img.add_to(m)
    folium.LayerControl().add_to(m)
    return m
