use pyo3::prelude::*;
use pyo3::types::PyBytes;

use pdf::file::File;

/// Checks that a byte array is a valid pdf
#[pyfunction]
fn check_is_valid_pdf(data: &PyBytes) -> PyResult<bool> {
    Ok(File::from_data(data.as_bytes()).is_ok())
}

/// A Python module implemented in Rust.
#[pymodule]
fn math_tavern_bot_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(check_is_valid_pdf, m)?)?;
    Ok(())
}