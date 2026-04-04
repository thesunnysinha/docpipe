import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import MuiLink from "@mui/material/Link";

export default function Footer() {
  return (
    <Box
      component="footer"
      sx={{ borderTop: "1px solid", borderColor: "divider", py: 5, textAlign: "center" }}
    >
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: "0.8125rem" }}>
          <Typography component="strong" sx={{ color: "text.primary", fontWeight: 600 }}>
            docpipe
          </Typography>{" "}
          is open source under the MIT License.
          <br />
          <MuiLink
            href="https://github.com/thesunnysinha/docpipe"
            target="_blank"
            rel="noopener noreferrer"
            color="primary.light"
            underline="hover"
          >
            GitHub
          </MuiLink>
          {" · "}
          <MuiLink
            href="https://pypi.org/project/docpipe-sdk/"
            target="_blank"
            rel="noopener noreferrer"
            color="primary.light"
            underline="hover"
          >
            PyPI
          </MuiLink>
          {" · "}
          <MuiLink
            href="https://github.com/thesunnysinha/docpipe/blob/main/CHANGELOG.md"
            target="_blank"
            rel="noopener noreferrer"
            color="primary.light"
            underline="hover"
          >
            Changelog
          </MuiLink>
          {" · "}
          <MuiLink
            href="https://github.com/thesunnysinha/docpipe/blob/main/CONTRIBUTING.md"
            target="_blank"
            rel="noopener noreferrer"
            color="primary.light"
            underline="hover"
          >
            Contributing
          </MuiLink>
        </Typography>
      </Container>
    </Box>
  );
}
