#Compares the .tsv files resulting from morph analysis
#Accepts 2 input directories
#The directory structures must be identical, there are no control mechanisms in place, yet.
#Outputs the line where the difference occured and also 5 lines preceding and after it.
#Author: Gerth Jaanimäe
import os
import sys
if len(sys.argv) < 3:
	sys.stderr.write("You must specify two directories to compare the files inside of them.\nUsage: compare_analyses_tsv.py <directory1> <directory2>\n")
	sys.exit(1)
dir1=sys.argv[1]
dir2=sys.argv[2]
diff_count=0
if os.path.isdir(dir1) and os.path.isdir(dir2):
		for root, dirs, files in os.walk(dir1):
			if len(files) > 0:
				for file in files:
					if not file.endswith(".tsv"):
						continue
					lines1=[]
					with open(os.path.join(root, file), encoding="utf-8") as fin:
						for line in fin:
							lines1.append(line.strip("\n"))
						lines2=[]
					with open(os.path.join(root.replace(dir1, dir2), file), encoding="utf-8") as fin:
						for line in fin:
							lines2.append(line.strip("\n"))
					for i in range(len(lines1)):
						if i==len(lines2):
							diff_count+=1
							break
						if lines1[i]!=lines2[i]:
							print (os.path.join(root, file))
							diff_count+=1
							for j in range(i-5, i+5):
								try:
									print (j, "A:", lines1[j])
									print ("B:", lines2[j])
								except IndexError:
									continue
							break
print (diff_count, " differing files in total.")