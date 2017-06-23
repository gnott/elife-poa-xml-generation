import unittest
import os
from mock import mock, patch
import zipfile
import shutil
import glob
from types import MethodType

os.sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import test settings last in order to override the regular settings
import poa_test_settings as settings

import importlib
transform = importlib.import_module("transform-ejp-zip-to-hw-zip")

import decapitatePDF2

def override_settings():
    # For now need to override settings to use test data
    transform.input_dir = settings.EJP_INPUT_DIR
    transform.output_dir = settings.STAGING_TO_HW_DIR
    transform.hw_ftp_dir = settings.FTP_TO_HW_DIR
    transform.tmp_dir = settings.TMP_DIR
    transform.decap_dir = settings.STAGING_DECAPITATE_PDF_DIR

def create_test_directories(dir_names=None):
    default_dir_names = []
    if dir_names is not None:
        default_dir_names = default_dir_names + dir_names

    for dir_name in default_dir_names:
        try:
            os.mkdir(dir_name)
        except OSError:
            pass


class TestTransformZip(unittest.TestCase):

    def setUp(self):
        override_settings()
        self.JUNK_DIR = settings.TEST_TEMP_DIR + "junk"
        self.basic_directories = [settings.TEST_TEMP_DIR, self.JUNK_DIR]
        self.transform_directories = [settings.EJP_INPUT_DIR, settings.STAGING_TO_HW_DIR,
            settings.FTP_TO_HW_DIR, settings.TMP_DIR, settings.STAGING_DECAPITATE_PDF_DIR]
        create_test_directories(self.basic_directories + self.transform_directories)
        self.decap_pdf = settings.XLS_PATH + 'transform' + os.sep + 'decap_elife_poa_e12717.pdf'
        self.zipfile_name = settings.XLS_PATH + 'transform' + os.sep + '18022_1_supp_mat_highwire_zip_268991_x75s4v.zip'

    def cleanup_directories(self):
        "to clean up between tests move the files into the junk directory"
        for dir_name in self.transform_directories:
            for file_path in glob.glob(dir_name + "/*"):
                file_name = file_path.split(os.sep)[-1]
                shutil.move(file_path, self.JUNK_DIR + os.sep + file_name)

    def test_extract_pdf_from_zipfile(self):
        "for test coverage"
        self.assertEqual(transform.extract_pdf_from_zipfile("test"), "this is a pdf")

    def test_manifestXML(self):
        "for test coverage"
        doi = "10.7554/eLife.12717"
        with zipfile.ZipFile(self.zipfile_name, 'r') as new_zipfile:
            manifest = transform.manifestXML(doi, new_zipfile)
            manifest.extended_manifest(new_zipfile)

    def test_get_file_contents_description(self):
        "for test coverage"
        doi = "10.7554/eLife.12717"
        with zipfile.ZipFile(self.zipfile_name, 'r') as new_zipfile:
            manifest = transform.manifestXML(doi, new_zipfile)
            self.assertEqual(manifest.get_file_contents_description(new_zipfile),
                             ' The zip folder contains 29 files including: 1 xml, 13 pdf, 2 xls, 12 mov, 1 xlsx.')

    def fake_copy_pdf_to_hw_staging_dir(self, decap_pdf, junk_a, junk_b, junk_c, junk_d):
        source_doc = decap_pdf
        pdf_filename = decap_pdf.split(os.sep)[-1]
        dest_doc = settings.STAGING_DECAPITATE_PDF_DIR + os.sep + pdf_filename
        shutil.copy(source_doc, dest_doc)

    def test_process_zipfile_12717(self):
        decap_pdf = self.decap_pdf
        zipfile_name = self.zipfile_name
        supp_files_zip_name = settings.TMP_DIR + os.sep + 'elife12717_Supplemental_files.zip'
        supp_file_count = 27

        output_dir = settings.TEST_TEMP_DIR

        # mock the PDF decapitation by copying the PDF file over
        transform.copy_pdf_to_hw_staging_dir = (
            MethodType(self.fake_copy_pdf_to_hw_staging_dir, decap_pdf))

        transform.process_zipfile(zipfile_name, output_dir)

        # verify
        with zipfile.ZipFile(supp_files_zip_name, 'r') as supp_zip_file:
            self.assertEqual(supp_file_count, len(supp_zip_file.namelist()), )

        # cleanup
        self.cleanup_directories()

    def test_process_zipfile_01466(self):
        "example with a transparent reporting form"
        # can use any PDF file here for this test
        decap_pdf = self.decap_pdf
        zipfile_name = settings.XLS_PATH + 'transform' + os.sep + '6744_1_supp_mat_highwire_zip_69348_2rn9t0.zip'
        supp_files_zip_name = settings.TMP_DIR + os.sep + 'elife01466_Supplemental_files.zip'
        supp_file_count = 1

        output_dir = settings.TEST_TEMP_DIR

        # mock the PDF decapitation by copying a PDF file over
        transform.copy_pdf_to_hw_staging_dir = (
            MethodType(self.fake_copy_pdf_to_hw_staging_dir, decap_pdf))

        transform.process_zipfile(zipfile_name, output_dir)

        # verify
        with zipfile.ZipFile(supp_files_zip_name, 'r') as supp_zip_file:
            self.assertEqual(supp_file_count, len(supp_zip_file.namelist()), )

        # cleanup
        self.cleanup_directories()


if __name__ == '__main__':
    unittest.main()
