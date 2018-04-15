import matplotlib
matplotlib.use("Agg")

class sdvel_on_map(object):
    """ A class to load and overlay various types of radar data """

    def __init__(self, mapObj, ax, rads, stime,
                 interval=120,
                 map_lat0=90, map_lon0=0,
                 map_width=50*111e3, 
                 map_height=50*111e3, 
                 map_resolution='l', 
                 rot_map=0.0,
                 coords="mlt",
                 channel=None,
                 fileType="fitacf"):

        from davitpy import utils
        import datetime

        self.stime = stime
        self.interval = interval
        self.etime = stime+datetime.timedelta(seconds=interval)
        self.rads = rads
        self.coords = coords
        self.fileType = fileType
        self.channel = channel
        self.ax = ax

        
        # rotate the map
        map_lon0 += rot_map
    
        # draw the actual map we want
        self.map_obj = mapObj

        # load the data, create sites and fovs for rads
        self.data = self._load_sddata()

    def _load_sddata(self):
        """ Loads radar data for period of interest"""

        from davitpy import pydarn

        # open the data files
        myPtrs = []
        for i in range(len(self.rads)):
            if self.channel:
                channel = self.channel[i]
            else:
                channel = self.channel
            # print "rad---->", self.rads[i], self.rads
            f = pydarn.sdio.radDataOpen(self.stime, self.rads[i],
                    self.etime, filtered=False,
                    fileType=self.fileType,
                    channel=channel)
            # print "f---------->", f
            if f is not None :
                myPtrs.append(f)
            else:
                myPtrs.append(None)
    
        #go through all open files
        sites, fovs, nrangs=[],[],[]
        rads_data = [[] for i in range(len(myPtrs))]
        for i in range(len(myPtrs)):
            myBeam = pydarn.sdio.radDataReadRec(myPtrs[i])

            #check that we have good data at this time
            if (myPtrs[i] is None) or (myBeam is None):
                myPtrs[i].close()
                rads_data[i] = None
                fovs.append(None)
                sites.append(None)
                nrangs.append(None)
                continue
            else:
                nrangs.append(myBeam.prm.nrang)
                        # create site object
                t=myPtrs[i].sTime
                site = pydarn.radar.site(radId=myBeam.stid,dt=t)
                sites.append(site)
            
                # create fov object
                myFov = pydarn.radar.radFov.fov(site=site, rsep=myBeam.prm.rsep,\
                                ngates=myBeam.prm.nrang+1,
                                nbeams=site.maxbeam, coords=self.coords,
                                date_time=t)
                fovs.append(myFov)

            # read until we reach the end of the time window
            while(myBeam is not None):
                if (myBeam.time > myPtrs[i].eTime): 
                    break
                if (myBeam.time >= myPtrs[i].sTime):
                    rads_data[i].append(myBeam)
                    myBeam = myPtrs[i].readRec()

                if rads_data[i] == []:
                    rads_data[i] = None

        self.sites = sites
        self.fovs = fovs
        return rads_data


    def overlay_radName(self, fontSize=15, annotate=True):
        """ Overlay radar names """

        from davitpy import pydarn
        for i, r in enumerate(self.rads):
            pydarn.plotting.overlayRadar(self.map_obj, codes=r, 
                         dateTime=self.stime,
                         fontSize=fontSize,
                         annotate=annotate)
        return

    def overlay_radFov(self, maxGate=70):
        """overlay radar fields of view"""

        from davitpy import pydarn

        for i,r in enumerate(self.rads):
            pydarn.plotting.overlayFov(self.map_obj, codes=r, 
                           dateTime=self.stime,
                           maxGate=maxGate,
                           fovObj=self.fovs[i])
        return

    def overlay_raw_data(self, param="velocity",
               gsct=0, fill=True,
               velscl=1000., vel_lim=[-1000, 1000],
                           srange_lim=[450, 4000],
               zorder=4,alpha=1,
               cmap=None,norm=None):

        """Overlays raw LOS data from radars""" 

        from davitpy import pydarn
        import numpy as np
        import math
        from matplotlib.collections import PolyCollection, LineCollection
        
        losvel_mappable = None
        for i in range(len(self.data)):
            if self.data[i] is None:
                continue

            fov = self.fovs[i]
            site = self.sites[i]
            myData = self.data[i]
            gs_flg,lines = [],[]
            if fill:
                verts,intensities = [],[]
            else:
                verts = [[],[]]
                intensities = []

            #loop through gates with scatter
            for myBeam in myData:
                for k in range(len(myBeam.fit.slist)):
                    if myBeam.fit.slist[k] not in fov.gates:
                        continue
                    if (myBeam.fit.slist[k] * myBeam.prm.rsep < srange_lim[0]) or\
                       (myBeam.fit.slist[k] * myBeam.prm.rsep > srange_lim[1]): 
                        continue

                    # if (myBeam.fit.v[k] < vel_lim[0]) or\
                    #    (myBeam.fit.v[k] > vel_lim[1]): 
                    #     continue
                    
                    r = myBeam.fit.slist[k]
                    if fill:
                        x1,y1 = self.map_obj(fov.lonFull[myBeam.bmnum,r],
                                             fov.latFull[myBeam.bmnum,r])
                        x2,y2 = self.map_obj(fov.lonFull[myBeam.bmnum,r+1],
                                             fov.latFull[myBeam.bmnum,r+1])
                        x3,y3 = self.map_obj(fov.lonFull[myBeam.bmnum+1,r+1],
                                             fov.latFull[myBeam.bmnum+1,r+1])
                        x4,y4 = self.map_obj(fov.lonFull[myBeam.bmnum+1,r],
                                             fov.latFull[myBeam.bmnum+1,r])
        
                        # save the polygon vertices
                        verts.append(((x1,y1),(x2,y2),(x3,y3),(x4,y4),(x1,y1)))

                    else:
                        x1,y1 = self.map_obj(fov.lonCenter[myBeam.bmnum,r],
                         fov.latCenter[myBeam.bmnum,r])
                        verts[0].append(x1)
                        verts[1].append(y1)
                        x2,y2 = self.map_obj(fov.lonCenter[myBeam.bmnum,r+1],
                         fov.latCenter[myBeam.bmnum,r+1])
                        theta = math.atan2(y2-y1,x2-x1)
                        x2 = x1+myBeam.fit.v[k]*velscl*(-1.0)*math.cos(theta)
                        y2 = y1+myBeam.fit.v[k]*velscl*(-1.0)*math.sin(theta)
                        lines.append(((x1,y1),(x2,y2)))

                    if(gsct):
                        gs_flg.append(myBeam.fit.gflg[k])

                    #save the param to use as a color scale
                    if(param == 'velocity'):
                        intensities.append(myBeam.fit.v[k])


            #do the actual overlay
            if fill :
                #if we have data
                if(verts != []):
                    if(gsct == 0):
                        inx = np.arange(len(verts))
                    else:
                        inx = np.where(np.array(gs_flg)==0)
                        # x = PolyCollection(np.array(verts)[np.where(np.array(gs_flg)==1)],
                        #                    facecolors='.3',linewidths=0,
                        #                    zorder=zorder+1,alpha=alpha)
                        # self.map_obj.ax.add_collection(x, autolim=True)
                    coll = PolyCollection(np.array(verts)[inx],
                                       edgecolors='face',linewidths=0,
                                       closed=False,zorder=zorder,
                                       alpha=alpha, cmap=cmap,norm=norm)
                    #set color array to intensities
                    coll.set_array(np.array(intensities)[inx])
                    self.map_obj.ax.add_collection(coll, autolim=True)

            else:
                #if we have data
                if(verts != [[],[]]):
                    if(gsct == 0):
                        inx = np.arange(len(verts[0]))
                    else:
                        inx = np.where(np.array(gs_flg)==0)

                        #plot the ground scatter as open circles
                        x = self.map_obj.ax.scatter(\
                                    np.array(verts[0])[np.where(np.array(gs_flg)==1)],
                                                    np.array(verts[1])[np.where(np.array(gs_flg)==1)],
                                        s=1.0, zorder=zorder,marker='o',linewidths=.5,
                                    facecolors='w',edgecolors='k')
                        self.map_obj.ax.add_collection(x, autolim=True)
        
                    # plot the i-s as filled circles
                    ccoll = self.map_obj.ax.scatter(np.array(verts[0])[inx],
                            np.array(verts[1])[inx],
                            s=1.0,zorder=zorder+1,marker='o',
                            c=np.array(intensities)[inx],
                            linewidths=.5, edgecolors='face',
                            cmap=cmap,norm=norm)

                    #set color array to intensities
                    self.map_obj.ax.add_collection(ccoll)

                    #plot the velocity vectors
                    coll = LineCollection(np.array(lines)[inx],linewidths=.5,
                       zorder=zorder+2,cmap=cmap,norm=norm)
                    coll.set_array(np.array(intensities)[inx])
                    self.map_obj.ax.add_collection(coll)

            if coll:
                losvel_mappable = coll
        self.losvel_mappable=losvel_mappable
        return
