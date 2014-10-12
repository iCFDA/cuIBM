#!/usr/bin/env python

import os
import argparse
import numpy as np
import numpy.linalg as la
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, os.path.expandvars("${CUIBM_DIR}/scripts/python"))
from readData import readSimulationParameters, readGridData, readVelocityData, readMask
import subprocess
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def main():
	# Command line options
	parser = argparse.ArgumentParser(description="Calculates the order of convergence.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument("-folder", dest="caseDir", help="folder in which the cases for different mesh sizes are present", default=os.path.expandvars("${CUIBM_DIR}/cases/convergence/cavityRe100/NavierStokes/20x20"))
	parser.add_argument("-tolerance", dest="tolerance", help="folder in which the cases for different mesh sizes are present", default=1.e-8)
	parser.add_argument("-interpolation_type", dest="interpolation_type", help="the type of interpolation used in the direct forcing method", default="linear")
	parser.add_argument("-run_simulations", dest="runSimulations", help="run the cases if this flag is used", action='store_true', default=False)
	parser.add_argument("-remove_mask", dest="removeMask", help="use values from the entire domain", action='store_true', default=False)
	args = parser.parse_args()

	# list of folders from which velocity data is to be obtained
	folders = sorted(os.walk(args.caseDir).next()[1], key=int)
	numFolders = len(folders)

	# run the cases in each of the folders
	if args.runSimulations:
		for folder in folders:
			runCommand = [os.path.expandvars("${CUIBM_DIR}/bin/cuIBM"),
							'-caseFolder', "{}/{}".format(args.caseDir, folder),
							'-velocityTol', "{}".format(args.tolerance),
							'-poissonTol', "{}".format(args.tolerance),
							'-interpolationType', "{}".format(args.interpolation_type)]
			print " ".join(runCommand)
			subprocess.call(runCommand)

	# create arrays to store the required values
	U = []
	V = []
	errNormU  = np.zeros(numFolders-1)
	errNormV  = np.zeros(numFolders-1)
	meshSize = np.zeros(numFolders-1, dtype=int)

	print ' '

	stride = 1
	for fIdx, folder in enumerate(folders):
		# path to folder
		folderPath = os.path.expandvars("{}/{}".format(args.caseDir, folder));
		# read simulation information
		nt, _, _, _ = readSimulationParameters(folderPath)

		# read the grid data
		# nx and ny are the number of cells
		# dx and dy are the cell widths
		# xu and yu are the coordinates of the locations where U is calculated
		nx, ny, dx, dy, xu, yu, xv, yv = readGridData(folderPath)
		
		if fIdx==0:
			initialMeshSpacing = dx[0]
		else:
			meshSize[fIdx-1] = nx

		# read velocity data
		u, v = readVelocityData(folderPath, nt, nx, ny, dx, dy)

		if not args.removeMask:
			# read mask
			mask_u, mask_v = readMask(folderPath, nx, ny)
			u[:] = u[:]*mask_u[:]
			v[:] = v[:]*mask_v[:]

		U.append(np.reshape(u, (ny, nx-1))[stride/2::stride,stride-1::stride])
		V.append(np.reshape(v, (ny-1, nx))[stride-1::stride,stride/2::stride])
		
		print 'Completed folder {}. u:{}, v:{}'.format(folder, U[fIdx].shape, V[fIdx].shape)
		stride = stride*3

	for idx in range(numFolders-1):
		errNormU[idx] = la.norm(U[idx+1]-U[idx])
		errNormV[idx] = la.norm(V[idx+1]-V[idx])
		
		if idx==0:
			h = initialMeshSpacing
			x = np.arange(h/2., 1., h)
			y = np.arange(h, 1., h)
			X, Y = np.meshgrid(x,y)
			plt.ioff()
			fig = plt.figure()
			ax = fig.add_subplot(111)
			diffV = np.abs(V[idx+1]-V[idx] )
			CS = ax.pcolor(X, Y, diffV, norm=LogNorm(vmin=1e-10, vmax=1))
			fig.gca().set_aspect('equal', adjustable='box')
			fig.colorbar(CS)
			if args.removeMask:
				fig.savefig("{}/diff_nomask.png".format(args.caseDir))
			else:
				fig.savefig("{}/diff.png".format(args.caseDir))
	
	orderOfConvergenceU = -np.polyfit(np.log10(meshSize), np.log10(errNormU), 1)[0]
	orderOfConvergenceV = -np.polyfit(np.log10(meshSize), np.log10(errNormV), 1)[0]
	
	print "\nMesh sizes: {}".format(meshSize)
	
	print "\nU:"
	print "errNorms: {}".format(errNormU)
	print "Convergence rates: {:.3f}, {:.3f}".format(np.log(errNormU[0]/errNormU[1])/np.log(3), np.log(errNormU[1]/errNormU[2])/np.log(3))
	print "Linear fit convergence rate: {:.3f}".format(orderOfConvergenceU)

	print "\nV:"
	print "errNorms: {}".format(errNormV)
	print "Convergence rates: {:.3f}, {:.3f}".format(np.log(errNormV[0]/errNormV[1])/np.log(3), np.log(errNormV[1]/errNormV[2])/np.log(3))
	print "Linear fit convergence rate: {:.3f}\n".format(orderOfConvergenceV)
	
	plt.clf()
	plt.loglog(meshSize, errNormU, 'o-b', label="L-2 norm of difference in $u$\nOrder of convergence={:.3f}".format(orderOfConvergenceU))
	plt.loglog(meshSize, errNormV, 'o-r', label="L-2 norm of difference in $v$\nOrder of convergence={:.3f}".format(orderOfConvergenceV))
	plt.axis([1, 1e4, 1e-4, 100])
	x  = np.linspace(1, 1e4, 2)
	x1 = 1/x
	x2 = 1/x**2
	plt.loglog(x, x1, '--k', label="First-order convergence")
	plt.loglog(x, x2, ':k', label="Second-order convergence")
	plt.legend()
	ax = plt.axes()
	ax.set_xlabel("Mesh size")
	ax.set_ylabel("L-2 Norm of difference between solutions on consecutive grids")
	plt.savefig("{}/convergence.png".format(args.caseDir))

if __name__ == "__main__":
	main()