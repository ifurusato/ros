#!/usr/bin/gnuplot -persist
#
# config for plotting PID output

set autoscale x
set xrange [0:0.01]
set autoscale y
#set yrange [0:70]
#set xdata time
set timefmt "%M%S"
#set format x "%M%S"
set title "PID: power vs. velocity" center
set key title "legend" left

#set style line 1  linecolor rgb "#efefef" linewidth 2.0 dashtype solid pointtype 1 pointsize default pointinterval 0
set style line 1  linecolor rgb "#ff6f00" linewidth 2.0 dashtype solid pointtype 1 pointsize default pointinterval 0

#set style line 2  linecolor rgb "#efefef" linewidth 2.0 dashtype solid pointtype 2 pointsize default pointinterval 0
set style line 2  linecolor rgb "#468dff" linewidth 2.0 dashtype solid pointtype 2 pointsize default pointinterval 0

set style line 3  linecolor rgb "#8d46ff" linewidth 2.0 dashtype solid pointtype 2 pointsize default pointinterval 0

set xtics 0.5
#set ytics 10.0
set xlabel "Time (sec)"
set ylabel "Percentage"
set grid
#set view 70, 30, 1, 1
set datafile separator whitespace
set style data points
set style function lines
#set term pdfcairo font "Times,10"
#set term png font "/home/pi/os/.fonts/Dosis-Medium.ttf"

# plot data ..........................................................
plot "data/slew.dat" using 1:2 title 'power' with lines ls 1,\
     "data/slew.dat" using 1:3 title 'actual velocity' with lines ls 2,\
     "data/slew.dat" using 1:4 title 'target velocity' with lines ls 3

#    EOF

