import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import PipelineSection from "@/components/PipelineSection";
import RAGSection from "@/components/RAGSection";
import FeaturesSection from "@/components/FeaturesSection";
import UsageSection from "@/components/UsageSection";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <PipelineSection />
      <RAGSection />
      <FeaturesSection />
      <UsageSection />
      <Footer />
    </main>
  );
}
