#!/bin/bash
git submodule update
rm -fr grits-bundle
mkdir grits-bundle
tar -pczf grits-bundle.tar.gz grits-bundle
