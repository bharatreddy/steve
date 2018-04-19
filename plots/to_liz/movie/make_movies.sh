echo $1
pdfcrop movie-plot.pdf
mv movie-plot-crop.pdf movie-plot.pdf
pdftocairo -png movie-plot.pdf
convert -delay 100 frames -loop 0 movie-plot-*.png movie-plot.gif
rm *.png