
import os;
import sys;
import string;
import math;

import random;
import time
import numpy;

import logging


import findTrinucleotideRepeats
import getAlignment
import UnsymmetricPairAlignment
from myheader import *
import myHMM
import useUnsymmetricalAlign


def readList(fname, mtype=int):
	f = open(fname,'r')
	mlines = f.readlines();
	data = [];
	for ml in mlines:
		mlsp = ml.split();
		curd = []
		for curi in mlsp:
			curi = string.strip(curi);
			if not curi=='': curd.append(mtype(curi));
		data.append(curd);
	f.close();
	return data;

def writeList(fname, mlist):
	f = open(fname, 'w')
	for ml in mlist:
		for ml1_ind in range(len(ml)):
			if ml1_ind==len(ml)-1: f.write(str(ml[ml1_ind])+'\n')
			else: f.write(str(ml[ml1_ind])+'\t')
	f.close();


def create_quality_for_pacbio_read(length, mean, sd):
    qualities = [fastq_Sanger_quality[min(max(0, int(random.gauss(mean, sd))), 93)] for i in range(length)]
    return ''.join(qualities)

def get3part(mgloc, gene_start_end, repeat_start_end, repeatgene, unique_file_id, analysis_file_id, hgfn): #='hg38.fa'):
	mytest = False;
	if mytest:# or repeatgene=='aff2':
		print repeatgene, gene_start_end, repeat_start_end
		print '\t', findTrinucleotideRepeats.getGene(repeatgene, mgloc[0], repeat_start_end)

	logging.info('The region is %s from %d to %d' % (mgloc[0], gene_start_end[0], gene_start_end[1]))
	
	mfasta = findTrinucleotideRepeats.getGene(repeatgene, mgloc[0], gene_start_end, unique_file_id, analysis_file_id, hgfn)
	
	upstreamstr = mfasta[:(repeat_start_end[0]-gene_start_end[0])]
	repregion   = mfasta[(repeat_start_end[0]-gene_start_end[0]):-(gene_start_end[1]-repeat_start_end[1])]
	downstreamstr = mfasta[-(gene_start_end[1]-repeat_start_end[1]):]

	if mytest: # or repeatgene=='aff2':
		print '\t', len(mfasta), len(upstreamstr), len(repregion), len(downstreamstr), len(upstreamstr)+len(repregion)+len(downstreamstr);
		print '\t', repregion

	return [upstreamstr, repregion, downstreamstr]

def getMidPos(seq, na3):
	findpos = False;

	for pos in range(int(len(seq)*0.45), len(seq)-2):
		if seq[pos:(pos+len(na3))]==na3: #seq[pos:(pos+3)]==na3:
			findpos = True;
			break;
	if findpos: return pos;
	else: return 0;

def getNA3fromRegion(seq, na3):
	patlen = len(na3);
	
	poslist = []; lenlist = []
	loci = 0; preloci = 0;
	while loci<len(seq)-patlen: #3:
		if seq[loci:loci+patlen] == na3:
			if preloci<loci:
				poslist.append(preloci); lenlist.append(loci-preloci);
			poslist.append(loci); lenlist.append(patlen);
			loci = loci + patlen;
			preloci = loci;
		else: loci += 1;
	if preloci<loci:
		poslist.append(preloci); lenlist.append(len(seq)-preloci);
	elif preloci<len(seq) and loci<len(seq):
		poslist.append(preloci); lenlist.append(len(seq)-preloci);

	plen = 0; #
	while True:
		while lenlist[plen]>patlen:
			poslist.insert(plen+1, poslist[plen]+patlen);
			lenlist.insert(plen+1, lenlist[plen]-patlen);
			lenlist[plen] = patlen;
			plen += 1;
		
		plen += 1;
		if plen >= len(poslist): break;
	
	return [poslist, lenlist];

def getRandomNA(bp):
	#print bp;
	prob = int(random.uniform(1,len(bp)))-1
	return bp[prob];

def mutateStr(seq, insert_rate, del_rate, sub_rate, bp5):
	seqlen = len(seq);
	insert_num = int(seqlen*insert_rate); #if insert_num<1: insert_num = 1;
	del_num = int(seqlen*del_rate); #if del_num<1: del_num = 1;
	sub_num = int(seqlen*sub_rate); #if sub_num<1: sub_num = 1;

	mmin = 0;
	insert_num = int(random.gauss(insert_num, 2)+0.5); 
	if insert_num<mmin: insert_num = mmin;
	del_num = int(random.gauss(del_num, 1)+0.5); 
	if del_num<mmin: del_num = mmin;
	sub_num = int(random.gauss(sub_num, 1)+0.5); 
	if sub_num<mmin: sub_num = mmin;

	#insertion could occur in the same position
	insert_pos = [random.randint(0,seqlen-1) for _ in xrange(insert_num)]; insert_pos.sort();
	#del_pos    = [random.random_integers(0,seqlen-1) for _ in xrange(del_num)];    del_pos.sort();
	allpos = range(seqlen);
	if del_num==0: del_pos=[] # deletion could not occur in the same position
	else: del_pos = random.sample(allpos, del_num); del_pos.sort();
	#sub_pos    = [random.random_integers(0,seqlen-1) for _ in xrange(sub_num)];    sub_pos.sort();
	if sub_num==0: sub_pos = [] # substitution could occur in the smae position
	else: sub_pos = random.sample(allpos, sub_num); sub_pos.sort();

	newstr = ''
	curp = 0; ij, dj, sj = 0, 0, 0;
	while curp < seqlen:
		while ij<insert_num and insert_pos[ij]==curp:
			newstr += getRandomNA(bp5[''])
			ij += 1;
		
		if dj<del_num and del_pos[dj]==curp:
			dj += 1;
		else:
			while sj<sub_num and sub_pos[sj]<curp: sj += 1;

			if sj<sub_num and sub_pos[sj]==curp:
				newstr += getRandomNA(bp5[seq[curp]]);
				sj += 1;
			else: newstr += seq[curp]

		curp += 1;

	if ij<insert_num-1: logging.warning("Not all insert positions are used: used=%d, total=%d with largest position=%d and current position=%d for seqlen=%d" % (ij, insert_num, insert_pos[-1], insert_pos[ij], seqlen));
	if dj<del_num-1: logging.warning("Not all deletion positions are used: used=%d, total=%d with largest position=%d and current position=%d for seqlen=%d" % (dj, del_num, del_pos[-1], del_pos[dj], seqlen))
	if sj<sub_num-1: logging.warning("Not all substitution positions are used: used=%d, total=%d with largest position=%d and current position=%d for seqlen=%d" % (sj, sub_num, sub_pos[-1], sub_pos[sj], seqlen))

	return newstr;

def mutateStr_bk(seq, insert_rate, del_rate, sub_rate, bp5):
        seqlen = len(seq);
        insert_prob = [random.uniform(0,1)<=insert_rate for _ in xrange(seqlen)]
        del_prob = [random.uniform(0,1)<=del_rate for _ in xrange(seqlen)]
        sub_prob = [random.uniform(0,1)<=sub_rate for _ in xrange(seqlen)]

        newstr = ''
        curp = 0;
        while curp < seqlen:
                if insert_prob[curp]:
                        curinsert = True;
                        while curinsert:
                                newstr += getRandomNA(bp5[''])
                                curinsert = random.uniform(0,1)<=insert_rate

                if not del_prob[curp]:
                        if sub_prob[curp]: newstr += getRandomNA(bp5[seq[curp]]);
                        else: newstr += seq[curp]

                curp += 1;

        return newstr;

def useUnsymmetricalAlign_old(upstreamstr, repregion, downstreamstr, curreadfile, repeatgene, repPat, forw_rerv, isRemInDel, isupdown, isExtend, currep2, bandwo):
	pdebug = False; 
	#if currep2[0]>=60 or currep2[1]>=60:
	if currep2[0]>=70 and currep2[1]>=70:
		pdebug = True;
	mdebug = False;
	if mdebug:
		print 'upstreamstr', len(upstreamstr), upstreamstr
		print 'repregion', len(repregion), repregion
		print 'downstreamstr', len(downstreamstr), downstreamstr

	templatestr = upstreamstr+repregion+downstreamstr;

	bandw = bandwo; # + int(len(templatestr)*0.2)
	#bandw = bandw*2

	if mdebug or pdebug: print '\ntemp_all  :', len(templatestr[len(upstreamstr)-10:-len(downstreamstr)]), templatestr[len(upstreamstr)-10:-len(downstreamstr)], 'bandw=', bandw
	print '\ntemp_all  :', len(templatestr[len(upstreamstr)-10:-len(downstreamstr)]), templatestr[len(upstreamstr)-10:-len(downstreamstr)], 'bandw=', bandw
	allsimreads = findTrinucleotideRepeats.myReadTxtFile(curreadfile)

	repregion_len_threhold = len(repPat);
	repeatbeforeafter = isupdown
	#toleratebeforeafter = 60;
	toleratebeforeafter = 30+isupdown;
	if toleratebeforeafter>len(upstreamstr): toleratebeforeafter = len(upstreamstr)-1
	if toleratebeforeafter>len(downstreamstr): toleratebeforeafter = len(downstreamstr)-1

	repeatlength = []; replen = len(repregion)
	
	hmmoptions = findTrinucleotideRepeats.getHMMOptions(repeatbeforeafter, repPat, forw_rerv)
	
	#for j in range(1, len(allsimreads), 4):
	for j in range(len(allsimreads)-3, 0, -4):
		if mdebug: print j, 
		querystr = allsimreads[j];
		#alignres = UnsymmetricPairAlignment.unsymmetricPairWiseAlignment(templatestr[::-1], len(templatestr), querystr[::-1], len(querystr), match, mismatch, gap_in_perf, gap_in_read, gap_before_after, bandw, 0).split(';')
		alignres = UnsymmetricPairAlignment.unsymmetricPairWiseAlignment(templatestr, len(templatestr), querystr, len(querystr), match, mismatch, gap_in_perf, gap_in_read, gap_before_after, bandw, 0).split(';')
		#alignres[0] = alignres[0][::-1]
		#alignres[1] = alignres[1][::-1]
		
		if mdebug: print 'done: '
		if mdebug or pdebug: print 'temp_first', len(templatestr), len(alignres[1]), len(alignres[1][len(upstreamstr)-10:-len(downstreamstr)]), alignres[1][len(upstreamstr)-10:-len(downstreamstr)]
		if mdebug or pdebug: print 'quey_first', len(querystr), len(alignres[0]), len(alignres[0][len(upstreamstr)-10:-len(downstreamstr)]), alignres[0][len(upstreamstr)-10:-len(downstreamstr)]
		res_temp = alignres[1].replace('-','');
		
		start_loc = templatestr.index(res_temp)
		if start_loc==-1:
			logging.error("Could not find the positio of aligned templates %s in %s" % res_temp, templatestr)
		
		if start_loc>=len(upstreamstr):
			logging.warning("Could not cover upstream (%d: %s) using aligned sequence %s for all %s" % (start_loc, upstreamstr, res_temp, templatestr))
		else:
			align_temp_i, query_i = 0, 0;
			start_repeat_loc = -1;
			end_repeat_loc = -1;
			temp_loc_start = [start_loc, 0, 0]; 
			consider3 = [upstreamstr, repregion, downstreamstr]
			beforenum = 0; afternum = 0;
			for i in range(len(temp_loc_start)):
				temp_i = temp_loc_start[i]
				curstreamstr = consider3[i]
				
				while temp_i<len(curstreamstr) and align_temp_i<len(alignres[1]):
					if alignres[1][align_temp_i]=='-':
						align_temp_i += 1;
						query_i += 1
					else:
						if not alignres[1][align_temp_i]==curstreamstr[temp_i]:
							logging.error("%d: template upstream (%s at %d) is different from aligned template (%s at %d)" % (i, curstreamstr[temp_i], temp_i, alignres[1][align_temp_i], align_temp_i))
						temp_i += 1
						align_temp_i += 1;
						query_i += 1
					if i==0 and temp_i<len(curstreamstr)-toleratebeforeafter:
						start_repeat_loc = query_i
					elif i==1 or i==2 and temp_i<toleratebeforeafter:
						end_repeat_loc = query_i
					if align_temp_i<len(alignres[0]) and (not (alignres[0][align_temp_i]=='-') ):
                                                if i==0: beforenum += 1
                                                if i==2: afternum += 1
			if  beforenum<isupdown or afternum<isupdown:
				logging.warning("Partial cover: orignal [start_repeat_loc, end_repeat_loc]=[%d, %d], [beforenum, afternum]=[%d, %d]< %d" % (start_repeat_loc, end_repeat_loc, beforenum, afternum, isupdown))
				logging.warning("Partial cover: query="+alignres[0][start_repeat_loc:end_repeat_loc+1])
				logging.warning("Partial cover: templ="+alignres[1][start_repeat_loc:end_repeat_loc+1])
				logging.warning("0="+alignres[0])
				logging.warning("1="+alignres[1])
				logging.warning("templatestr"+str(len(templatestr))+"="+templatestr)
				logging.warning("querystr"+str(len(querystr))+"="+querystr)
			if beforenum<isupdown:
                                logging.warning("Partial cover: befor="+alignres[1][:start_repeat_loc])
                                start_repeat_loc = -1
			if afternum<isupdown:
                                logging.warning("Partial cover: after="+alignres[1][end_repeat_loc+1:])
                                end_repeat_loc = -1

			if end_repeat_loc<len(upstreamstr)+len(repregion)+1:
                                logging.warning("Could not cover the whole repeat regions %d" % end_repeat_loc);
				
			if (start_repeat_loc==-1 or end_repeat_loc==-1) or end_repeat_loc-start_repeat_loc<repregion_len_threhold:
				logging.warning("Could not find the alignment %d result. The repeat region is %d, %d, " % (j, start_repeat_loc, end_repeat_loc));
			else:
				res_query = alignres[0].replace('-','');
				
				repeat_start_end = [start_repeat_loc, end_repeat_loc+1]
				repeat_start_end[0] -= isExtend; repeat_start_end[1] += isExtend;
				if isExtend>0 and repeat_start_end[0]<0: repeat_start_end[0]=0
				if isExtend>0 and repeat_start_end[1]>len(res_query)-1:
					repeat_start_end[1] = len(res_query)-1
			
	
				if mdebug or pdebug: print 'temp_rep', len(alignres[1][repeat_start_end[0]:repeat_start_end[1]]), alignres[1][repeat_start_end[0]:repeat_start_end[1]]
				if mdebug or pdebug: print 'quer_rep', len(alignres[0][repeat_start_end[0]:repeat_start_end[1]]), alignres[0][repeat_start_end[0]:repeat_start_end[1]]
	
				detectregion = alignres[0][repeat_start_end[0]:repeat_start_end[1]].replace('-','');
	
				if mdebug or pdebug: print len(detectregion), repeat_start_end, detectregion
				
				if isRemInDel>0:
					newstr, pre0, predstats = findTrinucleotideRepeats.getUnsymAlignAndHMM(repPat, forw_rerv, repeatbeforeafter, hmmoptions, detectregion)

					#newstr, pre0, predstats = findTrinucleotideRepeats.getUnsymAlignAndHMM(repPat, forw_rerv, repeatbeforeafter, detectregion, match, mismatch, gap_in_perf, gap_in_read, gap_before_after)
				else:
					newstr, pre0, predstats = myHMM.hmmpred(detectregion, repPat, forw_rerv, hmmoptions, repeatbeforeafter)
				repeatlength.append(len(newstr)/len(repPat))
	p2, allocr = findTrinucleotideRepeats.get2Peaks(repeatlength)
	
	
	return [p2, allocr];

def getMynormNum(avg, std,  mmin, mmax, mstr):
	currn = int(numpy.random.normal(avg, std, 1)[0])
	trytimes = 0;
	while (currn<mmin or currn>mmax):
		currn = int(numpy.random.normal(avg, std, 1)[0])
		trytimes = trytimes + 1
		if trytimes>1000:
			logging.error("Cannot find a number for "+mstr+(": trytimes=%d" % (trytimes)))
			logging.error(asd)
	return currn

def getrandomstr(newup, currepeat, newdown):
	newrandstr = newup + currepeat + newdown
	lenall = len(newrandstr);
	lenfirst = len(newup)-1; avg1 = lenfirst/2
	lensecond = len(newdown)-1; avg2 = lensecond/2

	pos1 = getMynormNum(avg1, 10, 1, lenfirst-1, 'First random position')
	pos2 = getMynormNum(avg2, 10, 1, lensecond-1, 'Second random position')
	
	return newrandstr[pos1:(-pos2)]
def getNormalDist(avgnormrep, mmin, mmax):
	currn = getMynormNum(avgnormrep, 5, mmin, mmax, 'repeats')
	return currn

def getDefinedSizeDif(mmin, mmax, m_repeatSizeDif):
        if len(m_repeatSizeDif)==1:
                repeatSizeDif = [m_repeatSizeDif[0], m_repeatSizeDif[0]]
                #repeat1 = int(random.uniform(repeatrange[0][0]+repeatSizeDif[0], repeatrange[1][1]-repeatSizeDif[0]))
                #repeat2array = [repeat1-repeatSizeDif[0], repeat1+repeatSizeDif[0]]
                #repeat2 = repeat2array[int(random.uniform(0,len(repeat2array)-1)+0.5)]
        else:
                repeatSizeDif = [m_repeatSizeDif[0], m_repeatSizeDif[1]]

        repeat1 = int(random.uniform(mmin+repeatSizeDif[1], mmax-repeatSizeDif[1]))
        repeat2array = []
        for curr2 in range(repeat1-repeatSizeDif[1], repeat1+repeatSizeDif[1]+1):
                #print '##', repeat1, repeat1-repeatSizeDif[1], repeat1+repeatSizeDif[1], '>', curr2, repeat1-repeatSizeDif[0], repeat1+repeatSizeDif[0], not (curr2>repeat1-repeatSizeDif[0] and curr2<repeat1+repeatSizeDif[0]), repeat1, repeatSizeDif[0], repeatSizeDif[1]
                if not (curr2>repeat1-repeatSizeDif[0] and curr2<repeat1+repeatSizeDif[0]):
                        repeat2array.append(curr2);
        rep2ind = random.uniform(0,len(repeat2array)-1)
        #print '##', repeat1, repeat2array, rep2ind, int(rep2ind+0.5)
        repeat2 = repeat2array[int(rep2ind+0.5)]

        retrep = [repeat1, repeat2]; retrep.sort();

        return retrep


def getSimForGivenGene(commonOptions, specifiedOptions, moreOptions):	
#def getSimForGivenGene(mgloc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, repeatgene, gene_start_end, repeat_start_end, repeatrange=[5, 100], insert_rate=0.12, del_rate=0.02, sub_rate=0.02, coverage=300, isRemInDel=1, isupdown=90, isExtend=0, randTimes=100, isPartial=False):
	mgloc = moreOptions['mgloc']
	repeatgene = moreOptions['repeatgene']
	gene_start_end = moreOptions['gene_start_end']
	repeat_start_end = moreOptions['repeat_start_end']

	repeatrange = moreOptions['repeatrange']
	isPartial = moreOptions['isPartial']

	isRemInDel = commonOptions['isRemInDel']
	isupdown = commonOptions['isupdown']
	isExtend = commonOptions['isExtend']
	hgfile = commonOptions['hgfile']
	SeqDepth = commonOptions['SeqDepth']

	unique_file_id = specifiedOptions['unique_file_id']
	analysis_file_id = specifiedOptions['analysis_file_id']
	simulation_file_id = specifiedOptions['simulation_file_id']
	isUnsymAlign = specifiedOptions['isUnsymAlign']
	
	insert_rate = specifiedOptions['insert_rate']
	del_rate = specifiedOptions['del_rate']
	sub_rate = specifiedOptions['sub_rate']
	coverage = specifiedOptions['coverage']
	randTimes = specifiedOptions['randTimes']
	repeatSizeDif = specifiedOptions['repeatSizeDif']
	
	simfolder = 'sim_data/'
	if not os.path.isdir(simfolder): 
		os.system("mkdir "+simfolder);

	#unique_file_id = simulation_file_id + analysis_file_id

	simfile = simfolder + repeatgene + simulation_file_id
	if not os.path.isdir(simfile):
		os.system("mkdir "+simfile)

	avgnormrep = int(mgloc[6][1:])
	
	mgloc[1] = int(mgloc[1]);  mgloc[2] = int(mgloc[2]);
	mgloc[3] = int(mgloc[3]);  mgloc[4] = int(mgloc[4]);
	curupdown = 120 #90;   # curgenestart, currepstart
	if curupdown<isupdown: curupdown=isupdown
	curgenestart = [mgloc[3]-curupdown, mgloc[4]+curupdown]
	if curgenestart[0]<1: curgenestart[0] = 1;
	if curgenestart[0]<gene_start_end[0]: curgenestart[0]=gene_start_end[0]
	if curgenestart[1]>gene_start_end[1]: curgenestart[1]=gene_start_end[1]
	currepstart = [mgloc[3], mgloc[4]]

	upstreamstr, repregion, downstreamstr = get3part(mgloc, gene_start_end, repeat_start_end, repeatgene , unique_file_id, analysis_file_id, hgfile)
	predres = []

	if len(repregion)==0:
		logging.error("Not repeat region! please check!!"+repeatgene+(' gene_location=[%d, %d], repeat_location=[%d, %d]' % (gene_start_end[0], gene_start_end[1], repeat_start_end[0], repeat_start_end[1])));
		sys.exit(1);

	na3 = getAlignment.getPattern(mgloc[5], mgloc[6])
	
	pos = getMidPos(repregion, na3);

	logging.info("Simulation for "+repeatgene+(' gene_location=[%d, %d], repeat_location=[%d, %d]; upstreamsize=%d, downstreamsize=%d' % (gene_start_end[0], gene_start_end[1], repeat_start_end[0], repeat_start_end[1], repeat_start_end[0]-gene_start_end[0], gene_start_end[1]-repeat_start_end[1])))
	logging.info("Normal/Pathogenic repeats: %s; avgnormrep=%d" % (mgloc[7], avgnormrep))
	logging.info("Detect a point in the middle for more repeat insertion");	
	logging.info(repregion+' '+repregion[pos:(pos+3)]+' '+str(pos)+' '+na3)
	#logging.info(("Mutation info: insertion rate=%.2f, deletion rate=%.2f, substitution rate=%.2f, repeat range=[%d, %d]" % (insert_rate, del_rate, sub_rate, repeatrange[0], repeatrange[1])))
	#print repeatrange
	logging.info(("Mutation info: insertion rate=%.2f, deletion rate=%.2f, substitution rate=%.2f, normal_range=[%d, %d]/path_range=[%d, %d]" % (insert_rate, del_rate, sub_rate, repeatrange[0][0], repeatrange[0][1], repeatrange[1][0], repeatrange[1][1])))
	#print repregion, repregion[pos:(pos+3)], pos, na3

	bp = getAlignment.getBasePair(); bpkeys = bp.keys(); bpkeys.sort();
	bp5 = {}
	bp5[''] = bpkeys
	bp5['A'] = ['C', 'G', 'T']
	bp5['C'] = ['A', 'G', 'T']
	bp5['G'] = ['A', 'C', 'T']
	bp5['T'] = ['A', 'C', 'G']

	poslist, lenlist = getNA3fromRegion(repregion, na3);
	if True:
		posstr = ''
		for posind in range(len(poslist)):
			posstr += '|'
			for j in range(lenlist[posind]-1):
				posstr += ' '
		#print posstr
		#print repregion
	posind = range(1, len(poslist))
	

	#origstr = upstreamstr+repregion+downstreamstr
	orirepeat = int(len(repregion)/float(len(na3))) #3)

	#logging.info("Orignal simulation read="+upstreamstr+'<<<'+repregion+'>>>'+downstreamstr+(" #repeat=%d; #len=%d" % (orirepeat, len(repregion))))
	logging.info("Orignal simulation read="+'<<<'+repregion+'>>>'+(" #repeat=%d; #len=%d" % (orirepeat, len(repregion))))

	#bwamem_w_option = repeatrange[1]*4;
	bwamem_w_option = repeatrange[1][1]*4;
	max_w_option, min_w_option = 1000, 100;
	if bwamem_w_option<min_w_option: bwamem_w_option = min_w_option
	if bwamem_w_option>max_w_option: bwamem_w_option = max_w_option
	
	#bwamem_w_option = bwamem_w_option + int(len(upstreamstr+repregion+downstreamstr)*0.2)
	bwamem_w_option = bwamem_w_option + int(len(upstreamstr+repregion+downstreamstr)*0.5)

	logging.info("bwamem_w_option="+str(bwamem_w_option))

	#print mgloc
	#print unique_file_id, simulation_file_id, analysis_file_id, repeatgene, gene_start_end, repeat_start_end, repeatrange, insert_rate, del_rate, sub_rate, coverage, isRemInDel, isupdown, isExtend, randTimes
	#print repregion
	#sys.exit(1)
	
	previous_sim_repeats = []
	produced_repeat_file = simfile+'_produced_repeats.txt'
	if os.path.isfile(produced_repeat_file):
		previous_sim_repeats = readList(produced_repeat_file)
	cur_sim_repeats = []
	
	alwaysproduced = False; 
	alwaysproduced = True;
	randomproduced = False; #True; #False; #True;
	refcov = 10000; #9400
	refcov = 3000; 
	curcovstr = ('cov%d' % coverage)
	curcovind = simfile.index(curcovstr)
	refcovfolder = simfile[:curcovind]+('cov%d' % refcov)+simfile[(curcovind+len(curcovstr)):]
	if os.path.isfile(refcovfolder+'_produced_repeats.txt'):
		refcovrepeats = readList(refcovfolder+'_produced_repeats.txt')
	else: randomproduced = True;

	moreOptions['repeat_orig_start_end'] = [moreOptions['repeat_start_end'][0], moreOptions['repeat_start_end'][1]]
	moreOptions['chr'] = mgloc[0]
	moreOptions['repPat'] = mgloc[5];
	moreOptions['forw_rerv']= mgloc[6]

	
	for rt in range(randTimes):
		start_time = time.time();

		curreadfile = simfile + '/' + str(rt) +'.fastq'
		bamfile = curreadfile + '.bam'
		
		#moreOptions['bamfile'] = bamfile
		specifiedOptions['bamfile'] = bamfile
		specifiedOptions['fastafile'] = curreadfile

		#print rt, produced_repeat_file, '\n', moreOptions['bamfile'], '\n', unique_file_id, '\n', analysis_file_id, '\n', simulation_file_id

		if isUnsymAlign and os.path.isfile(curreadfile) and rt<len(previous_sim_repeats):
			currep2 = previous_sim_repeats[rt]
			cur_sim_repeats.append(currep2)
			
			logging.info("Simutlate repeats are %d and %d at %d round" % (currep2[0], currep2[1], rt))
			logging.info("File exist "+curreadfile)
		elif (not isUnsymAlign) and os.path.isfile(bamfile) and os.path.isfile(bamfile+'.bai') and rt<len(previous_sim_repeats) and rt<len(previous_sim_repeats):
			currep2 = previous_sim_repeats[rt]
			
			cur_sim_repeats.append(currep2)
			
			logging.info("Simutlate repeats are %d and %d at %d round" % (currep2[0], currep2[1], rt))
			logging.info("File exist "+bamfile)
		else: 
			if (randomproduced or alwaysproduced): # and rt<len(previous_sim_repeats):
				if len(repeatSizeDif)==0:
					#repeat1 = int(random.uniform(repeatrange[0][0], repeatrange[0][1]))
					repeat1 = getNormalDist(avgnormrep, repeatrange[0][0], repeatrange[0][1])
					repeat2 = int(random.uniform(repeatrange[1][0], repeatrange[1][1]))
				else:
					repeat1, repeat2 = getDefinedSizeDif(repeatrange[0][0], repeatrange[1][1], repeatSizeDif)
					
				currep2 = [repeat1, repeat2]; currep2.sort();
				cur_sim_repeats.append(currep2)
				
				logging.info("Simutlate repeats are %d and %d at %d round" % (currep2[0], currep2[1], rt))
			else: 
				currep2 = refcovrepeats[rt]
				cur_sim_repeats.append(currep2)
				
				refsq = findTrinucleotideRepeats.myReadTxtFile(refcovfolder+ '/' + str(rt) +'.fastq')
				
			
			allsimreads = [];
			currep2.sort(); num_long_reads = int(coverage/(1.5**(currep2[1]/float(currep2[0])-1))+0.5)
			logging.info("num_long_reads="+str(num_long_reads))
			
			for i in currep2:
				for j in range(coverage):
					if isPartial and i==currep2[1] and j>=num_long_reads: continue
					if not (randomproduced or alwaysproduced):
						if coverage*5<len(refsq):
							allsimreads.append(refsq[coverage*4]);
							allsimreads.append(refsq[coverage*4+1]);
							allsimreads.append(refsq[coverage*4+2]);
							allsimreads.append(refsq[coverage*4+3]);
							continue;

					if i < orirepeat:
						neworder = random.sample(posind, i);
						neworder.sort();
						newrepeat = ''
						for noi in neworder:
							newrepeat += repregion[poslist[noi]:(poslist[noi]+lenlist[noi])]
					else:
						curind = int(random.uniform(1, len(poslist)));
						if curind==0:
							newrepeat = (na3*(i-orirepeat)) + repregion
							#curpos = 0;
						elif curind==len(poslist)-1:
							newrepeat = repregion + (na3*(i-orirepeat))
							#curpos = len(poslist)-1
						else:
							curpos = poslist[curind]
							newrepeat = repregion[:curpos] + (na3*(i-orirepeat)) + repregion[curpos:]
					
					newup = mutateStr(upstreamstr, insert_rate, del_rate, sub_rate, bp5)
					currepeat = mutateStr(newrepeat, insert_rate, del_rate, sub_rate, bp5)
					newdown =  mutateStr(downstreamstr, insert_rate, del_rate, sub_rate, bp5)
					
					if j<3:
						logging.debug('Perf: '+('%.0f' % (len(newrepeat)/3))+'>>>'+newrepeat)
						logging.debug('Mutat:'+('%.0f' % (len(currepeat)/3))+'>>>'+currepeat)
					
					allsimreads.append('@'+repeatgene+':'+str(i)+':'+str(j))
					if isPartial: #allsimreads.append(newup+currepeat+newdown)
						allsimreads.append(newup+currepeat+newdown)
					else:
						newrandstr = getrandomstr(newup, currepeat, newdown)
						allsimreads.append(newrandstr)
					allsimreads.append('+')
					allsimreads.append(create_quality_for_pacbio_read(len(allsimreads[-2]), 30, 10));
		
			findTrinucleotideRepeats.myWriteTxtFile(allsimreads, curreadfile)

			if True: #not isUnsymAlign:
				#cmd = 'bwa mem -x pacbio -t 4 '+hg38_reference_and_index+'/hg38.fa '+ curreadfile +' | samtools view -S -b | samtools sort > '+bamfile
				#cmd = 'bwa mem -k17 -W40 -r10 -A2 -B2 -O2 -E2 -L3 -t 4 '+hg38_reference_and_index+'/hg38.fa '+ curreadfile +' | samtools view -S -b | samtools sort > '+bamfile
				cmd = 'bwa mem -k17 -w'+str(bwamem_w_option)+' -W40 -r10 -A1 -B1 -O1 -E1 -L1 -t 4 '+hg_reference_and_index+'/'+hgfile+' '+ curreadfile +' | samtools view -S -b | samtools sort > '+bamfile

				logging.info(cmd);
				os.system(cmd);
			
				cmd = 'samtools index '+bamfile
				os.system(cmd)

		if not isUnsymAlign:
			#print repeatgene, curgenestart, currepstart, bamfile, mgloc[5], mgloc[6], isRemInDel, isupdown, isExtend, unique_file_id, analysis_file_id
			p2all = findTrinucleotideRepeats.getRepeatForGivenGene(commonOptions, specifiedOptions, moreOptions)
			#p2all = findTrinucleotideRepeats.getRepeatForGivenGene(mgloc[0], repeatgene, curgenestart, currepstart, bamfile, mgloc[5], mgloc[6], isRemInDel, isupdown, isExtend, unique_file_id, analysis_file_id)
			p2 = p2all[2];
		else:
			#p2all = useUnsymmetricalAlign(upstreamstr, repregion, downstreamstr, curreadfile, repeatgene, mgloc[5], mgloc[6], isRemInDel, isupdown, isExtend, currep2, bwamem_w_option);
			p2all = useUnsymmetricalAlign.useUnsymmetricalAlign(upstreamstr, repregion, downstreamstr, curreadfile, repeatgene, mgloc[5], mgloc[6], isRemInDel, isupdown, isExtend, bwamem_w_option, False, currep2, True, SeqDepth);
			p2 = p2all[0];
			pbwa = findTrinucleotideRepeats.getRepeatForGivenGene2(commonOptions, specifiedOptions, moreOptions)
			#pbwa = findTrinucleotideRepeats.getRepeatForGivenGene2(mgloc[0], repeatgene, curgenestart, currepstart, bamfile, mgloc[5], mgloc[6], isRemInDel, isupdown, isExtend, unique_file_id, analysis_file_id)
			pbwa = pbwa[2];
			pbwa.sort();
			if len(pbwa)==1: pbwa = [pbwa[0], pbwa[0]]
			if len(pbwa)==0: pbwa = [0, 0]
			
	
		p2.sort();
		if len(p2)==1: p2 = [p2[0], p2[0]];
		if len(p2)==0: p2 = [0, 0];

		if isUnsymAlign:
			logging.info("Result for simutlation repeats are %d and %d at %d round: %s, %s (%s, %s); Elapsed time=%.2f\n" % (currep2[0], currep2[1], rt, str(p2[0]), str(p2[1]), str(pbwa[0]), str(pbwa[1]), (time.time() - start_time)))
		else:
			logging.info("Result for simutlation repeats are %d and %d at %d round: %s, %s; wrong alignment %d for %s. Elapsed time=%.2f\n" % (currep2[0], currep2[1], rt, str(p2[0]), str(p2[1]), p2all[5], bamfile, (time.time() - start_time)))
	
		if not isUnsymAlign:
			predres.append([currep2, p2, p2all[5]])
		else: predres.append([currep2, p2, pbwa])

	if len(previous_sim_repeats)<=len(cur_sim_repeats):	
		writeList(produced_repeat_file, cur_sim_repeats)
		
	return predres

def getRange1(str1):
	strsp = str1.split('/');
	normrange = [100000,0];
	for sp1 in strsp:
		curr = sp1.split('-')
		if len(curr)==1:
			curr = curr[0]
			if curr[-1]=='+': curr = curr[:-1];
			#print str1, curr
			curmin = int(curr);
			if curmin<normrange[0]: normrange[0] = curmin;
			if normrange[1]<curmin: normrange[1] = int(curmin * 1.25)
		elif len(curr)==2:
			curmin = int(curr[0]); curmax = int(curr[1]);
			if curmin<normrange[0]: normrange[0] = curmin;
			if curmax>normrange[1]: normrange[1] = curmax
	return normrange

def getRepeatRange2(mstr):
	strsp = mstr.split(':')
	normstr = strsp[0];     pathstr = strsp[1];
	normrange = getRange1(normstr);
	pathrange = getRange1(pathstr);
	return [normrange, pathrange]

def getRepeatRange(mstr):
	strsp = mstr.split(':')
	normstr = strsp[0];	pathstr = strsp[1];
	
	normrange = getRange1(normstr);
	pathrange = getRange1(pathstr);

	allrange = [normrange[0], pathrange[1]];
	if allrange[0]>pathrange[0]:
		logging.error("Too less repeat for Pathogenic:"+('Pathogenic=[%d, %d], Normal=[%d, %d]' % (pathrange[0], pathrange[1], normrange[0], normrange[1])))
	if pathrange[1]<normrange[1]: 
		logging.error("Too more repeat for Normal:"+('Pathogenic=[%d, %d], Normal=[%d, %d]' % (pathrange[0], pathrange[1], normrange[0], normrange[1])))

	if allrange[0]>=allrange[1]:
		logging.error("Wrong repeat range="+('[%d, %d]' % (allrange[0], allrange[1])))

	return allrange;

def getSimforKnownGeneWithPartialRev(commonOptions, specifiedOptions):
#def getSimforKnownGeneWithPartialRev(gLoc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, repeatgene, newinfo, insert_rate=0.12, del_rate=0.02, sub_rate=0.02, coverage=300, isRemInDel=1, isupdown=90, isExtend=0, randTimes=100):
	moreOptions = {}

	gLoc = commonOptions['gLoc']
	repeatgene = commonOptions['repeatgene']
	newinfo = commonOptions['specifiedGeneInfo']

        infospt = newinfo.split('/')
	repeatgene = repeatgene.lower()
	if gLoc.has_key(repeatgene):
		mgloc = gLoc[repeatgene]
	else: mgloc = ['','','', '','', '','','']

	if len(infospt)<len(mgloc):
		logging.error("Error: wrong input for the gene of interes: %s whose length is %d less than the expected length %d" % (newinfo, len(infospt), len(mgloc)));
		sys.exit(101);

	for i in range(len(mgloc)):
		curnew = string.strip(infospt[i]);
		if not curnew=='': 
			mgloc[i] = curnew
	errorstr = ''
	for i in range(len(mgloc)):
		if string.strip(mgloc[i])=='':
			errorstr += ('Error no information for %d\n' % i)
	if not errorstr=='':
		logging.error(errorstr);
		sys.exit(102);

	gene_start_end = [int(mgloc[1]), int(mgloc[2])]
	repeat_start_end = [int(mgloc[3]), int(mgloc[4])]
	repeatrange = getRepeatRange(mgloc[7])
	repeatrange = getRepeatRange2(mgloc[7])

	moreOptions['gene_start_end'] = gene_start_end
	moreOptions['repeat_start_end'] = repeat_start_end
	moreOptions['mgloc'] = mgloc
	moreOptions['repeatgene'] = commonOptions['repeatgene']
	moreOptions['repeatrange'] = repeatrange
	moreOptions['isPartial'] = True;

	#print mgloc; sys.exit(103);

	res = getSimForGivenGene(commonOptions, specifiedOptions, moreOptions)
        #res = getSimForGivenGene(mgloc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, repeatgene, gene_start_end, repeat_start_end, repeatrange, insert_rate, del_rate, sub_rate, coverage, isRemInDel, isupdown, isExtend, randTimes, True)
	
	return res

def getSimforKnownGene(commonOptions, specifiedOptions):
#                  0         1             2            3            4         5     6     7
#gloc['fmr1'] = ['chrX', '147911951', '147951127', '14799051', '147912110', 'CGG', '+', '6-53:230+/55-200']
#def getSimforKnownGene(gLoc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, repeatgene, insert_rate=0.12, del_rate=0.02, sub_rate=0.02, coverage=300, isRemInDel=1, isupdown=90, isExtend=0, randTimes=100):
	#defaultupdownstreamsize = 5000;
	moreOptions = {}

	gLoc = commonOptions['gLoc']
	repeatgene = commonOptions['repeatgene']	
	
	repeatgene = repeatgene.lower()
	mgloc = findTrinucleotideRepeats.get_gLoc(repeatgene, gLoc);

	repeatrange = getRepeatRange(mgloc[7])
	defaultupdownstreamsize = repeatrange[1]*25;
	maxupdown = 6000; minupdown = 4000;
	maxupdown = 1000; minupdown = 800;
	if defaultupdownstreamsize>maxupdown: defaultupdownstreamsize = maxupdown
	elif defaultupdownstreamsize<minupdown: defaultupdownstreamsize = minupdown;
	#defaultupdownstreamsize = 5000;	

	gene_start_end = [int(mgloc[1]), int(mgloc[2])]
	repeat_start_end = [int(mgloc[3]), int(mgloc[4])]

	#if repeat_start_end[0] - gene_start_end[0] < defaultupdownstreamsize: # upstreampos:
	#	upstreampos = gene_start_end[0] 
	#else:
	#	upstreampos = repeat_start_end[0] - defaultupdownstreamsize
	#
	#if gene_start_end[1] - repeat_start_end[1] < defaultupdownstreamsize:
	#	downstreampos = gene_start_end[1]
	#else:
	#	downstreampos = repeat_start_end[1] + defaultupdownstreamsize

	upstreampos = repeat_start_end[0] - defaultupdownstreamsize
	if upstreampos<1: upstreampos = 1
	downstreampos = repeat_start_end[1] + defaultupdownstreamsize

	gene_start_end = [upstreampos, downstreampos]
	repeatrange = getRepeatRange2(mgloc[7])

	moreOptions['gene_start_end'] = gene_start_end
	moreOptions['repeat_start_end'] = repeat_start_end
	moreOptions['mgloc'] = mgloc
	moreOptions['repeatgene'] = commonOptions['repeatgene']
	moreOptions['repeatrange'] = repeatrange
	moreOptions['isPartial'] = False;

	res = getSimForGivenGene(commonOptions, specifiedOptions, moreOptions)
	#res = getSimForGivenGene(mgloc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, repeatgene, gene_start_end, repeat_start_end, repeatrange, insert_rate, del_rate, sub_rate, coverage, isRemInDel, isupdown, isExtend, randTimes, False)
        
	return res;


def getSim(commonOptions, specifiedOptions):
#def getSim(gLoc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, insert_rate=0.12, del_rate=0.02, sub_rate=0.02, coverage=300, isRemInDel=1, isupdown=90, isExtend=0, randTimes=100):
	res = []

	glkeys = gLoc.keys(); glkeys.sort()
	for glk in glkeys:
		commonOptions['repeatgene'] = glk
		res.extend(getSimforKnownGene(commonOptions, specifiedOptions))
		#res.extend(getSimforKnownGene(gLoc, isUnsymAlign, unique_file_id, simulation_file_id, analysis_file_id, glk, insert_rate, del_rate, sub_rate, coverage, isRemInDel, isupdown, isExtend, randTimes));

	return res;

if __name__=="__main__":
	
	LOG_FILENAME = "log/mytest_useUnsymmetricalAlign.txt"

	logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO,filemode='w',format="%(levelname)s: %(message)s")

	gLoc = findTrinucleotideRepeats.getDiseseGeneInRefGenomeLocation('hg38')
	
	repPat = 'CTG';  forw_rerv = '+'
	repeatgene = 'atxn3'; mgloc = gLoc[repeatgene]; ra = [35, 37]  #  35, 57
	curreadfile = 'sim_data/atxn3_defpcr1_ins0.12_del0.02_sub0.02_cov100/1.fastq'
	gene_location = [92070888, 92072403]; repeat_location=[92071011, 92071052]
	unique_file_id, analysis_file_id = 'mytest_useUnsymmetricalAlign_unique', 'mytest_useUnsymmetricalAlign_analysis'
	
	curreadfile = 'sim_data/atxn3_ins0.12_del0.02_sub0.02_cov1900/1.fastq'; ra = [69, 70]
	curreadfile = 'sim_data/atxn3_ins0.12_del0.02_sub0.02_cov1600/55.fastq'; ra = [43, 81]
	gene_location = [int(mgloc[1]), int(mgloc[2])]
	repeat_location = [int(mgloc[3]), int(mgloc[4])]
	
	gene_location = [int(mgloc[3])-2150, int(mgloc[4])+2150]
	
	upstreamstr, repregion, downstreamstr = get3part(mgloc, gene_location, repeat_location, repeatgene , unique_file_id, analysis_file_id)

	#print useUnsymmetricalAlign(upstreamstr, repregion, downstreamstr, curreadfile, repeatgene, repPat, forw_rerv, 0, 0, 3, ra, 400)
	#print 'dif'
	print useUnsymmetricalAlign(upstreamstr, repregion, downstreamstr, curreadfile, repeatgene, repPat, forw_rerv, 1, 18, 0, ra, 400)


