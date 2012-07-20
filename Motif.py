#!/usr/bin/env python
# encoding: utf-8
"""
Motif.py

Created by Graham Tremper on 2012-07-10.
"""
import sys
import os
import random
import cPickle as pickle
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import graph_helper as gh
from collections import defaultdict

USECACHE = False

def convertIDToGraph(id, motifSize, save=False):
	"""Plot graph with id and motifSize"""
	binary = bin(id);
	adj = np.zeros(motifSize*motifSize)
	l = 0
	for x in xrange(1,motifSize*motifSize+1):
		if binary[-x+l] == 'b':
			break
		if (x-1) % (motifSize+1) == 0:
			l += 1
		else:
			adj[-x] = int(binary[-x+l])
	adj.shape = (motifSize,motifSize)
	graph = nx.to_networkx_graph(adj,create_using=nx.DiGraph())
	nx.draw_circular(graph)
	if save:
		plt.savefig("result/id-"+str(id)+"size-"+str(motifSize))
	else:
		plt.show()
	plt.clf()

def genRandMats(num):
	"""Generate random adjacency matricies"""
	mats = []
	for i in xrange(num):
		x = np.random.rand(88,88)
		x -= np.diag(np.diag(x))
		mats.append(x)
	return mats

def findMotifs(data,key,motifSize=3,degree=10,randGraphs=None):
	"""Main finding motifs routine"""

	#Check cache
	filename = "" if randGraphs is None else "RAND"
	filename += str(key)+'s'+str(int(motifSize))+'d'+str(int(degree))+".pkl"
	if os.path.exists('cache/'+filename) and USECACHE:
		print "in cache"
		with open('cache/'+filename,"rb") as f:
			return pickle.load(f)
	
	#generate random matricies
	if key == "rand":
		graphs = genRandMats(100)
	else:
		graphs = data[key]

	motifs = defaultdict(list)
	numstring ="/"+str(len(graphs))
	rejected = 0
	for index,G in enumerate(graphs):
		#Cull bad graphs
		if np.count_nonzero(G)<len(G)*degree:
			rejected += 1
			continue

		#calculate threshold
		sortedWeights = np.sort(G,axis=None)
		threshold = sortedWeights[-len(G)*degree-1]
		#Print progress
		sys.stdout.write("\rMotif Finding Progress: "+str(index)+numstring)
		sys.stdout.write(" Threshold: "+str(threshold))
		sys.stdout.flush()

		#Output graph to txt file
		graph = nx.DiGraph(G>threshold)
		graph = nx.convert_node_labels_to_integers(graph,1)
		if randGraphs is not None:
			graph = randGraphs[key][index]
		with open('result/OUTPUT.txt','wb') as f:
			f.write(str(len(graph)) + '\n')
			nx.write_edgelist(graph,f,data=False)
		
		#Jenky way to use c++ motif finder in python
		os.system("./Kavosh "+str(motifSize))
		with open("result/MotifCount.txt","rb") as f:
			subgraphs = float(f.next())
			data = np.loadtxt(f, ndmin=2)
		
		for iD,total in data:
			percent = total/subgraphs
			motifs[int(iD)].append(percent)
			
	print '\nMotifs Done! Graphs Rejected: '+str(rejected)

	#add zeros to graphs that didn't contain motifs
	for key,value in motifs.iteritems():
		numZero = len(graphs)-len(value)-rejected
		value.extend([0 for derp in xrange(numZero)])
		motifs[int(key)] = np.array(value)

	motifs = dict(motifs)
	#add motifs to cache
	if USECACHE:
		with open('cache/'+filename,'wb') as f:
			pickle.dump(motifs,f)

	return motifs

def plotMotifGraphs(data,motifSize=3,degree=10,numofmotifs=10,usetotal=False):
	"""Draws graph compairing average motif count between samples in the data"""
	for corr in ('corr','lcorr','lacorr'):

		nl=findMotifs(data,('NL',corr), motifSize, degree,usetotal)
		mci=findMotifs(data,('MCI',corr), motifSize, degree,usetotal)
		ad=findMotifs(data,('AD',corr), motifSize, degree,usetotal)

		motifs = nl.items()
		motifs = sorted(motifs,key=lambda x:-x[1].mean())
		keys = [int(key) for key,value in motifs[:numofmotifs]]

		meansNL = []
		meansMCI = []
		meansAD = []
		stdNL = []
		stdMCI = []
		stdAD = []
		for key in keys:
			meansNL.append(nl[key].mean() if key in nl else 0.)
			stdNL.append(nl[key].std() if key in nl else 0.)
			meansMCI.append(mci[key].mean() if key in mci else 0.)
			stdMCI.append(mci[key].std() if key in mci else 0.)
			meansAD.append(ad[key].mean() if key in mci else 0.)
			stdAD.append(ad[key].std() if key in mci else 0.)

		ind = np.arange(numofmotifs)
		width = 0.2 

		NLplt = plt.bar(ind, meansNL, width, color='b', yerr=stdNL, ecolor='y')
		MCIplt = plt.bar(ind+width, meansMCI, width, color='y', yerr=stdMCI, ecolor='b')
		ADplt = plt.bar(ind+width+width, meansAD, width, color='g', yerr=stdAD, ecolor='r')

		plt.ylabel('Average number of motifs')
		plt.xlabel('Motif ID')
		plt.title('Motif size '+str(motifSize) +' distribution for '+corr+" with average degree "+str(degree))
		plt.xticks(ind+width+width/2., keys)
		plt.ylim(ymin=0.0)
		plt.legend( (NLplt[0], MCIplt[0], ADplt[0]), ('NL', 'MCI', 'AD') )
		plt.grid(True)
		header = 'result/TotalMotifDis-' if usetotal else 'result/PercentMotifDis-'
		plt.savefig(header+corr+"_D-"+str(degree)+"_S-"+str(motifSize))
		plt.clf()

def PDFstats(data, filename, edgeSwap=False, motifSize=3, degree=10):
	"""Output a latex pdf of motif stats"""
	filename = "result/" + filename + ".tex"

	if not edgeSwap:
		motifsNLRAND = motifsMCIRAND = motifsADRAND = motifsCONVERTRAND = findMotifs(data,"rand",motifSize=motifSize,degree=degree)

	with open(filename,'wb') as f:
		f.write(
		"\\documentclass{article}\n"
		"\\usepackage{amsmath,fullpage,graphicx,fancyhdr,xcolor,colortbl,chngpage}\n"
		"\\usepackage[landscape]{geometry}"
		"\\definecolor{yellow}{RGB}{255,255,70}\n"
		"\\definecolor{orange}{RGB}{255,165,70}\n"
		"\\definecolor{red}{RGB}{255,70,70}\n"
		"\\title{Motif Data}\n"
		"\\author{Graham Tremper}\n"
		"\\date{}\n"
		"\\fancyhead{}\n"
		"\\begin{document}\n"
		)
		
		if edgeSwap:
			with open("SwapData"+str(degree)+".pkl","rb") as pic:
				randGraphs = pickle.load(pic)
		
		statistics = {}		
		for corr in ('corr','lcorr','lacorr'):
			print "Starting " + corr +"..."
			motifsNL = findMotifs(data, ('NL',corr), motifSize = motifSize, degree=degree)
			motifsMCI = findMotifs(data, ('MCI',corr), motifSize = motifSize, degree=degree)
			motifsAD = findMotifs(data, ('AD',corr), motifSize = motifSize, degree=degree)
			motifsCONVERT = findMotifs(data, ('CONVERT',corr), motifSize = motifSize, degree=degree)
			if edgeSwap:
				motifsNLRAND = findMotifs(data, ('NL',corr), motifSize = motifSize, degree=degree, randGraphs=randGraphs)
				motifsMCIRAND = findMotifs(data, ('MCI',corr), motifSize = motifSize, degree=degree, randGraphs=randGraphs)
				motifsADRAND = findMotifs(data, ('AD',corr), motifSize = motifSize, degree=degree, randGraphs=randGraphs)
				motifsCONVERTRAND = findMotifs(data, ('CONVERT',corr), motifSize = motifSize, degree=degree, randGraphs=randGraphs)

			allMotifs = list( set(motifsNL.keys())
							& set(motifsAD.keys())
							& set(motifsMCI.keys())
							& set(motifsCONVERT.keys())
							& set(motifsNLRAND.keys())
							& set(motifsMCIRAND.keys())
							& set(motifsADRAND.keys())
							& set(motifsCONVERTRAND.keys()) )

			motifStats = []
			for key in allMotifs:
				c1 = stats.ttest_ind(motifsNL[key], motifsMCI[key])
				c2 = stats.ttest_ind(motifsNL[key], motifsAD[key])
				c3 = stats.ttest_ind(motifsNL[key], motifsCONVERT[key])
				c4 = stats.ttest_ind(motifsMCI[key], motifsAD[key])
				c5 = stats.ttest_ind(motifsMCI[key], motifsCONVERT[key])
				c6 = stats.ttest_ind(motifsAD[key], motifsCONVERT[key])
				c7 = stats.ttest_ind(motifsNL[key], motifsNLRAND[key])
				c8 = stats.ttest_ind(motifsMCI[key], motifsMCIRAND[key])
				c9 = stats.ttest_ind(motifsAD[key], motifsADRAND[key])
				c10 = stats.ttest_ind(motifsCONVERT[key], motifsCONVERTRAND[key])
				motifStats.append((key,c1,c2,c3,c4,c5,c6,c7,c8,c9,c10))

			motifStats.sort(key=lambda x: motifsNL[x[0]].mean(),reverse=True)

			f.write(
			"\\begin{table}[t]\n"
			"\\begin{adjustwidth}{-1.5in}{-1.5in} "
			"\\caption{Motif T-test results from "+corr+" data with using edge swap}\n"
			"\\centering\n"
			"\\begin{tabular}{|c|c|c|c|c|c|c|c|c|c|c|}\n"
			"\\hline\n"
			"\\rowcolor[gray]{0.85}\n"
			"Key & NL to MCI & NL to AD & NL to Conv & MCI to AD & MCI to Conv & AD to Conv & NL to Rand & MCI to Rand & AD to Rand & Conv to Rand \\\\ \\hline\n"
			)
			for stat in motifStats:
				f.write( str(stat[0]) + " \\cellcolor[gray]{0.95}")
				for sign,col in stat[1:]:
					cell = " & {0:.3}".format(col)
					if sign > 0:
						cell += '(+)'
					else:
						cell += '(-)'

					if col <= 0.01:
						cell += " \\cellcolor{red} "
					elif col <= 0.05:
						cell += " \\cellcolor{orange}"
					elif col <= 0.1:
						cell += " \\cellcolor{yellow}"
					f.write(cell)
				f.write("\\\\ \\hline\n")

			f.write(
			"\\end{tabular}\n"
			"\\end{adjustwidth}"
			"\\end{table}\n"
			)

		f.write("\\end{document}\n")

	os.system("pdflatex -output-directory result " + filename)
	os.system("rm result/*.log result/*.aux")


def main():
	with open("aznorbert_corrsd_new.pkl","rb") as f:
		data = pickle.load(f)
		
	G = findMotifs(data,("AD","corr"),motifSize=3,degree=10)	
	
	#print "---Starting size 3---"
	#PDFstats(data, "MotifSize3", motifSize=3, edgeSwap=True)
	#print "---Starting size 4---"
	#PDFstats(data, "MotifSize4", motifSize=4, edgeSwap=True)
	#print "---Starting size 5---"
	#PDFstats(data, "MotifSize5", motifSize=5, edgeSwap=True)
	

	
def makeSwapData(degree=10):
	with open("aznorbert_corrsd_new.pkl","rb") as f:
		data = pickle.load(f)
		
	swapData = {}
	
	for key, graphs in data.iteritems():
		print key
		keyData = []
		for i,G in enumerate(graphs):
			print i
			sortedWeights = np.sort(G,axis=None)
			threshold = sortedWeights[-len(G)*degree-1]
        	
			graph = nx.DiGraph(G>threshold)
			diff = gh.randomize_graph(graph, 2500)
			keyData.append(graph)
		swapData[key] = keyData
	
	with open("SwapData"+str(degree)+".pkl",'wb') as f:
		pickle.dump(swapData,f)

if __name__ == '__main__':
	main()
