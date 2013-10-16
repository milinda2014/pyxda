#!/usr/bin/env python
# coding=utf-8
##############################################################################
#
# pyxda.srxes       X-ray Data Analysis Library
#                   (c) 2013 National Synchrotron Light Source II,
#                   Brookhaven National Laboratory, Upton, NY.
#                   All rights reserved.
#
# File coded by:    Michael Saltzman
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
##############################################################################

from chaco.tools.api import PanTool, ZoomTool, LineInspector, \
            ScatterInspector, RangeSelection, RangeSelectionOverlay
from chaco.api import ArrayPlotData, Plot, jet, BaseTool, add_default_axes, \
             add_default_grids, ScatterInspectorOverlay, LinearMapper, ColorBar
from chaco import default_colormaps
from enable.api import KeySpec
from traits.api import Any, HasTraits, Instance, Int, Event, Trait, Callable
import numpy as np

class KBInputTool(BaseTool):
    '''Tool that enables files to be switched with the arrow keys.'''
    
    arrow_cb = Any()
    left_key = KeySpec("Left",)
    right_key = KeySpec("Right",)

    def normal_key_pressed(self, event):
        if self.left_key.match(event):
            #print 'Left Arrow'
            self.arrow_cb(self, -1)
        elif self.right_key.match(event):
            #print 'Right Arrow'
            self.arrow_cb(self, 1)

class Display(HasTraits, object):
    '''Handles creation/modification of the plots in the GUI.
    
    |  jobqueue -- the event queue
    |  filenum -- the index of the new file to be plotted (based on 
    |             RR selection)
    |  cmap -- colormap for the imageplot
    |  _selection -- the range of the highlighted region drawn on the histogram
    '''

    def __init__(self, queue, **kwargs):
        super(Display, self).__init__()
        self.jobqueue = queue
        self.add_trait('filenum', Int())
        self.cmap = jet
        self._selection = None
    
    def _arrow_callback(self, tool, n):
        '''Internal function used by KBInputTool to put events on queue'''
        if n == 1:
            self.jobqueue.put(['updatecache', ['right']])
        else:
            self.jobqueue.put(['updatecache', ['left']])

    def _metadata_handler(self):
        '''Handles hover/click selections made in the RR plots
        
        Hovering over a point displays the filename of the image that point 
        represents in the control panel above. Clicking a point will display 
        the image that point represents on the left panel. Multiple click
        selections can be made but only the last selected image will be 
        displayed.
        '''
        sel_indices = self.index_datasource.metadata.get('selections', [])
        hover_indices = self.index_datasource.metadata.get('hover', [])
        #print "Selection indices:", sel_indices
        #print "Hover indices:", hover_indices
        if sel_indices:
            self.jobqueue.put(['changendx', [sel_indices[-1]]])
            #print sel_indices[-1]
        if hover_indices:
            self.filenum = int(hover_indices[0])
            #print 'self.filenum', self.filenum
        else:
            self.filenum = -1
        return

    def plotImage(self, image, plot=None):
        '''Plots a tiff image.

        |  image -- Image object
        |  plot  -- plot instance to be updated 
        |           if None, a plot instance will be created

        Returns the plot instance.
        '''
        if plot == None:
            pd = ArrayPlotData()
            pd.set_data('imagedata', image.data)
            plot = Plot(pd, default_origin = "bottom left", padding=0)
            plot.bgcolor = 'white'
            plot.fixed_preferred_size = (100, 100)
            plot.x_axis.visible = False
            plot.y_axis.visible = False
            self.imageplot = plot

            imgPlot = plot.img_plot("imagedata", colormap=self.cmap, 
                                                    name='image')[0]
            self.imgPlot = imgPlot
            self.appendImageTools(imgPlot)
        else:
            plot.data.set_data('imagedata', image.data)
        plot.aspect_ratio = float(image.data.shape[1]) / image.data.shape[0]
        plot.invalidate_and_redraw()
        return plot

    def plotRRMap(self, ydata, title, plot=None):
        '''Plots an RR map.

        |  ydata -- y-data to be plotted
        |  title -- RR type, to be displayed on y-axis
        |  plot  -- plot instance to be updated 
        |           if None, a plot instance will be created

        Returns the plot instance.
        '''
        if plot == None:
            pd = ArrayPlotData()
            plot = Plot(pd, padding=(79, 5, 0, 0))
            self.setData(ydata, None, plot)
            plot.plot(('x', 'y'), name='rrplot', type="scatter", color='green',
                      marker="circle", marker_size=6)
            plot.value_axis.title = title
            plot.bgcolor = 'white'
            plot.aspect_ratio = 2.5
            plot.fixed_preferred_size = (100, 50)
            plot.y_axis.tick_label_formatter = lambda val:('%.2E'%val)
            plot.x_axis.visible = False
            hgrid, vgrid = add_default_grids(plot)
            self.appendRRTools(plot)
        else:
            self.setData(ydata, None, plot)
        plot.invalidate_and_redraw()
        return plot

    def setData(self, ydata, xdata, plot):
        '''Convenience method for setting data in 1D plots.

        If xdata is None, then the x values are set to the indices of ydata.

        |  ydata -- numpy array of y values
        |  xdata -- numpy array of x values
        |  plot -- plot instance to be updated

        Returns the plot instance.
        '''
        if xdata == None:
            plot.data.set_data('x', range(len(ydata)))
        else:
            plot.data.set_data('x', xdata)
        plot.data.set_data('y', ydata)
        return

    def plotHistogram(self, image, plot=None):
        '''Plots a histogram.

        |  image -- Image object
        |  plot  -- plot instance to be updated 
        |           if None, a plot instance will be created

        Returns the plot instance.
        '''
        if plot == None:
            pd = ArrayPlotData(y=np.array([0]), x=np.array([0]))
            plot = Plot(pd, padding=(70, 10, 0, 0))
            plot.plot(('x', 'y'), name='Histogram', type='bar', bar_width=1.0)
            plot.line_color = 'black'
            plot.bgcolor = "white"
            plot.fixed_preferred_size = (100, 30)
            add_default_grids(plot)
            plot.value_range.low = 'auto'
            plot.value_range.high = 'auto'
            plot.index_range.low = 'auto'
            plot.index_range.high = 'auto'
            plot.value_axis.title = "Histogram"
            self.appendHistogramTools(plot)
            
        else:
            data = np.histogram(image.data, bins=10000)
            index = np.delete(data[1], data[1].size-1)
            values = data[0]
            self.setData(values, index, plot)
        plot.invalidate_and_redraw()
        return plot

    def plot1DCut(self, image, plot=None):
        '''Plots a 1D cut of the image.

        Currently, the 1D cut is a plot of mean intensity vs column #.

        |  image -- Image object
        |  plot  -- plot instance to be updated 
        |           if None, a plot instance will be created

        Returns the plot instance.
        '''
        if plot == None:
            pd = ArrayPlotData(y=np.array([0]), x=np.array([0]))
            plot = Plot(pd, padding=(70, 10, 0, 5))
            plot.plot(('x', 'y'), name='1D Cut', type='line', color='blue')
            plot.value_axis.title = '1D Cut'
            plot.x_axis.visible = False
            plot.bgcolor = "white"
            plot.fixed_preferred_size = (100, 30)
            plot.value_range.low = 'auto'
            plot.value_range.high = 'auto'
            plot.index_range.low = 'auto'
            plot.index_range.high = 'auto'
            self.append1DCutTools(plot)
        else:
            index = range(image.data.shape[1])
            values = image.data.mean(axis=0)
            self.setData(values, index, plot)
        plot.invalidate_and_redraw()
        return plot

    def appendImageTools(self, plot):
        '''Attach zoom, pan, arrow key input, and colorbar to image.

        |  Zoom Controls: 
        |                 'z' = ROI selection
        |                 'n' = backwards in zoom history
        |                 'm' = forwards in zoom history
        |                 mouse scroll = zoom in/out

        plot -- instance of ImagePlot to be given tools
        '''
        plot.tools.append(PanTool(plot))
        
        zoom = ZoomTool(component=plot, tool_mode="box", always_on=False,
                            color='transparent',
                            zoom_factor=1.25, pointer='sizing',
                            prev_state_key=KeySpec('n'),
                            next_state_key=KeySpec('m'),
                            x_min_zoom_factor = 1.0,
                            y_min_zoom_factor = 1.0
                            )
        plot.overlays.append(zoom)
        plot.zoom = zoom
        plot.tools.append(KBInputTool(plot, arrow_cb=self._arrow_callback))

        colormap = plot.color_mapper
        colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                        color_mapper=colormap,
                        plot=plot,
                        orientation='v',
                        resizable='v',
                        width=30,
                        padding=20)

        range_selection = RangeSelection(component=colorbar)
        colorbar.tools.append(range_selection)
        rangeselect = RangeSelectionOverlay(component=colorbar,
                                                   border_color="white",
                                                   alpha=0.8,
                                                   fill_color="lightgray")
        colorbar.overlays.append(rangeselect)
        range_selection.listeners.append(plot)
        self.colorbar = colorbar
        return
    
    def appendHistogramTools(self, plot):
        '''Attach zoom, pan, and rangeselect to plot.

        If a range is selected, this range of values will be highlighted in the
        image above.

        plot -- instance of Plot to be given tools
        '''
        zoom = ZoomTool(component=plot, tool_mode="box", always_on=False,
                            color='transparent',
                            zoom_factor=1.25, pointer='sizing',
                            enter_zoom_key=KeySpec('p'),
                            prev_state_key=KeySpec('n'),
                            next_state_key=KeySpec('m'),
                            x_min_zoom_factor = 1.0,
                            y_min_zoom_factor = 1.0
                            )
        plot.overlays.append(zoom)
        plot.zoom = zoom
        
        my_plot = plot.plots["Histogram"][0]

        my_plot.tools.append(PanTool(plot))
        self.range_selection = RangeSelection(component=my_plot)
        self.sync_trait('_selection', self.range_selection)

        my_plot.tools.append(self.range_selection)

        rangeselect = RangeSelectionOverlay(component=my_plot,
                                                   border_color="white",
                                                   alpha=0.8,
                                                   fill_color="lightgray")
        my_plot.overlays.append(rangeselect)
        self.range_selection.listeners.append(self.imgPlot)
        return

    # FIXME: Hover/Click selections only work for the last RR plot created.
    def appendRRTools(self, plot):
        '''Attach zoom, pan, and ScatterInspector to plot.

        Individual points can be selected. The last selected point will be 
        plotted. Hovering over a point will display the filename it refers to.

        plot -- instance of Plot to be given tools
        '''
        my_plot = plot.plots['rrplot'][0]
        self.index_datasource = my_plot.index
        self.index_datasource.on_trait_change(self._metadata_handler,
                                              "metadata_changed")
        my_plot.tools.append(ScatterInspector(my_plot, selection_mode="toggle",
                                          persistent_hover=False))

        my_plot.overlays.append(ScatterInspectorOverlay(my_plot,
                                hover_color = "transparent",
                                hover_marker_size = 10,
                                hover_outline_color = "purple",
                                hover_line_width = 2,
                                selection_marker_size = 8,
                                selection_color = "lawngreen")
                               )
        zoom = ZoomTool(component=plot, tool_mode='box', always_on=False, 
                            zoom_factor=1.25, color='transparent')
        plot.overlays.append(zoom)
        plot.tools.append(PanTool(plot))
        return

    def append1DCutTools(self, plot):
        '''Attaches zoom and pan tools to the plot.
        
        Zoom has same controls as the imageplot.
    
        plot -- instance of Plot to be given tools
        '''
        plot.tools.append(PanTool(plot))
        
        zoom = ZoomTool(component=plot, tool_mode="box", always_on=False,
                            color='transparent',
                            zoom_factor=1.25, pointer='sizing',
                            prev_state_key=KeySpec('n'),
                            next_state_key=KeySpec('m'),
                            x_min_zoom_factor = 1.0,
                            y_min_zoom_factor = 1.0
                            )
        plot.overlays.append(zoom)
        plot.zoom = zoom
        return

    # FIXME: The color map does not always update immediately. Sometimes you
    #        have to interact with the plot before it will apply the cmap.
    def updateColorMap(self, cmap):
        ''' Changes the colormap for the image plot.

        cmap -- the new color scheme
        '''
        self.cmap = cmap
        crange = self.imageplot.color_mapper.range
        cmapper = default_colormaps.color_map_name_dict[self.cmap](crange)
        self.imageplot.color_mapper = cmapper
        self.imageplot.invalidate_draw()
        return
