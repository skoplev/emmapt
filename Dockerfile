FROM debian:stable
RUN mkdir -p /bdmerge

# General installs
RUN apt-get update && apt-get install -y \
	apache2 \
	apache2-prefork-dev \
	libapache2-mod-wsgi \
	libhdf5-dev \
	libcurl4-gnutls-dev

RUN apt-get update && apt-get install -y \
	libssl-dev \
	libcurl4-openssl-dev \
	# required for R package XML
	libxml2-dev \
	curl \
	libnetcdf-dev

# Python installs
RUN apt-get update && apt-get install -y \
	python \
	python-dev \
	python-pip \
	python-setuptools \
	python-h5py

# R installs
RUN apt-get update && apt-get install -y \
	r-base  \
	r-base-dev \
	r-recommended

# pip installs
RUN pip install -Iv Flask==0.10.1
RUN pip install \
	numpy \
	cython \
	jsonpickle \
	h5py

# R Bioconductor installs
RUN Rscript -e "source('http://bioconductor.org/biocLite.R'); biocLite('affy'); biocLite('rhdf5')"

# configure R and install packages
RUN echo "r <- getOption('repos'); r['CRAN'] <- 'http://cran.us.r-project.org'; options(repos = r);" > ~/.Rprofile
RUN Rscript -e "install.packages('stringr')"
RUN Rscript -e "install.packages('data.table')"
RUN Rscript -e "install.packages('plyr')"
RUN Rscript -e "install.packages('GeoDE')"
RUN Rscript -e "install.packages('getopt')"
RUN Rscript -e "install.packages('rjson')"

 
EXPOSE 5000
 
ADD . /bdmerge

# install bdmerge library from the folder added
# RUN Rscript -e "library(devtools); install('bdmerge/lib/rlib/bdmerge')"
RUN Rscript -e "install.packages('/bdmerge/lib/rlib/bdmerge', repos=NULL, type='source')"


WORKDIR /bdmerge
CMD ./bdmerge.py