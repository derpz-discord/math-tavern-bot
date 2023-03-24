use pyo3::prelude::*;
use pyo3::types::PyBytes;

use pdf::file::File;
use pyo3::create_exception;



create_exception!(math_tavern_bot_rs, InvalidURL, pyo3::exceptions::PyException);

/// Checks that a byte array is a valid pdf
#[pyfunction]
fn check_is_valid_pdf(data: &PyBytes) -> PyResult<bool> {
    Ok(File::from_data(data.as_bytes()).is_ok())
}

/// Checks that a url is a valid pdf
#[pyfunction]
fn check_url_is_valid_pdf(url: &str) -> PyResult<bool> {
    let bytes = download_file_to_bytes(url);
    if bytes.is_err() {
        return Err(InvalidURL::new_err(format!("Invalid URL: {}", url)));
    }
    Ok(File::from_data(bytes.unwrap()).is_ok())
}

fn download_file_to_bytes(url: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut resp = reqwest::blocking::get(url)?;
    let mut bytes = Vec::new();
    resp.copy_to(&mut bytes)?;
    Ok(bytes)
}

/// A Python module implemented in Rust.
#[pymodule]
fn math_tavern_bot_rs(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(check_is_valid_pdf, m)?)?;
    m.add_function(wrap_pyfunction!(check_url_is_valid_pdf, m)?)?;
    m.add("InvalidURL", py.get_type::<InvalidURL>())?;
    Ok(())
}